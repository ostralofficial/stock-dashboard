import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks, get_client

st.set_page_config(page_title="종목 상세", page_icon="🔍", layout="wide")
st.header("종목 상세")

INCOME_ITEMS = ["매출액", "매출원가", "매출총이익", "판관비", "영업이익", "순이익", "EPS"]

ANNUAL_GROUPS = {
    "재무상태표": ["자산총계", "자본총계", "부채비율", "현금성자산", "매출채권", "재고자산", "단기차입금"],
    "현금흐름":   ["CFO", "주당CFO", "투자활동CF", "재무활동CF", "FCF", "주당FCF", "감가상각", "EBITDA"],
    "주주가치":   ["EPS", "EPS증가", "BPS", "DPS", "배당증가", "배당성향", "배당총액", "ROE", "ROE평균", "주식수"],
    "밸류에이션": ["PER", "PBR", "EV/EBITDA", "Ey", "psr", "적정가격", "RIM가격", "기대수익률", "10년가격"],
}

PREFERRED_ITEMS = ["매출액", "영업이익", "순이익", "DPS", "EPS", "CFO", "FCF", "매출총이익", "판관비"]

@st.cache_data(ttl=300, show_spinner="데이터 로딩 중...")
def load_stock_data(stock_code):
    client = get_client()
    res = (client.table("financials")
           .select("year, quarter, item, value")
           .eq("stock_code", stock_code)
           .order("year")
           .execute())
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def make_wide_table(df, item):
    """연도×분기 테이블: 연도=열, 분기=행"""
    sub = df[(df["item"] == item) & (df["quarter"].isin([0,1,2,3,4]))].copy()
    if sub.empty:
        return None
    q_map = {0:"연간", 1:"1Q", 2:"2Q", 3:"3Q", 4:"4Q"}
    sub["분기"] = sub["quarter"].map(q_map)
    pivot = sub.pivot_table(index="분기", columns="year", values="value", aggfunc="first")
    row_order = ["1Q", "2Q", "3Q", "4Q", "연간"]
    pivot = pivot.reindex([r for r in row_order if r in pivot.index])
    return pivot

def make_quarter_series(df, items):
    points = []
    sub = df[df["item"].isin(items) & df["quarter"].isin([1,2,3,4])]
    sub = sub.sort_values(["year", "quarter"])
    for _, row in sub.iterrows():
        points.append({
            "기간": f"{int(row['year'])}Q{int(row['quarter'])}",
            "값": row["value"],
            "항목": row["item"],
        })
    return points

@st.cache_data(ttl=300, show_spinner="주가 로딩 중...")
def load_price_quarterly(stock_code):
    try:
        import FinanceDataReader as fdr
        df = fdr.DataReader(stock_code, "2014-01-01")
        df.index = pd.to_datetime(df.index)
        df_q = df["Close"].resample("QE").last().dropna()
        labels = [f"{d.year}Q{d.quarter}" for d in df_q.index]
        return pd.Series(df_q.values, index=labels, name="주가")
    except:
        return None

def sort_periods(periods):
    """2014Q1 형식의 기간을 올바르게 정렬"""
    def key(p):
        try:
            y, q = p.split("Q")
            return int(y) * 10 + int(q)
        except:
            return 0
    return sorted(periods, key=key)

def make_combined_fig(pts_df, graph_items, price_s, sel_name, chart_type):
    """재무지표 + 주가 이중축 통합 차트"""
    all_periods = sort_periods(pts_df["기간"].unique()) if not pts_df.empty else []
    if price_s is not None:
        all_periods = sort_periods(set(all_periods) | set(price_s.index))

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 재무 지표 (왼쪽 축)
    for item in graph_items:
        sub = pts_df[pts_df["항목"] == item].sort_values("기간") if not pts_df.empty else pd.DataFrame()
        if sub.empty:
            continue
        if chart_type == "바":
            fig.add_trace(go.Bar(x=sub["기간"], y=sub["값"], name=item), secondary_y=False)
        else:
            fig.add_trace(go.Scatter(
                x=sub["기간"], y=sub["값"],
                mode="lines+markers", name=item, line=dict(width=2),
            ), secondary_y=False)

    # 주가 (오른쪽 축)
    if price_s is not None and not price_s.empty:
        fig.add_trace(go.Scatter(
            x=price_s.index, y=price_s.values,
            mode="lines", name="주가",
            line=dict(color="rgba(255,165,0,0.9)", width=2, dash="dot"),
        ), secondary_y=True)

    fig.update_layout(
        title=f"{sel_name} — 분기별 재무 + 주가",
        xaxis=dict(tickangle=-45, tickvals=all_periods[::4], categoryorder="array", categoryarray=all_periods),
        barmode="group",
        hovermode="x unified",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(b=80),
    )
    fig.update_yaxes(title_text="재무 지표", secondary_y=False)
    fig.update_yaxes(title_text="주가 (원)", secondary_y=True)
    return fig

def generate_pdf(sel_name, fin_df, fig):
    """plotly 차트 + 테이블을 HTML → PDF 변환"""
    try:
        import pdfkit
        html_parts = [f"<h1>{sel_name} 재무 분석</h1>"]

        # 손익 테이블
        html_parts.append("<h2>손익계산서 (분기별)</h2>")
        for item in INCOME_ITEMS:
            tbl = make_wide_table(fin_df, item)
            if tbl is None or tbl.dropna(how="all").empty:
                continue
            html_parts.append(f"<h3>{item}</h3>")
            html_parts.append(tbl.fillna("-").to_html(border=1))

        # 그래프 이미지
        html_parts.append("<h2>분기 그래프</h2>")
        img_bytes = fig.to_image(format="png", width=1200, height=500)
        import base64
        img_b64 = base64.b64encode(img_bytes).decode()
        html_parts.append(f'<img src="data:image/png;base64,{img_b64}" width="100%"/>')

        html_content = f"""
        <html><head><meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 11px; margin: 20px; }}
            h1 {{ font-size: 20px; }} h2 {{ font-size: 15px; }} h3 {{ font-size: 12px; color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 10px; }}
            td, th {{ border: 1px solid #ccc; padding: 4px 8px; text-align: right; }}
            th {{ background: #f0f0f0; }}
        </style></head><body>{"".join(html_parts)}</body></html>
        """
        pdf_bytes = pdfkit.from_string(html_content, False)
        return pdf_bytes
    except ImportError:
        return None

# ── UI ───────────────────────────────────────────────────
stocks_df = get_all_stocks()
if stocks_df.empty:
    st.info("종목을 먼저 추가해주세요")
    st.stop()

sel_name = st.selectbox("종목 선택", options=stocks_df["name"].tolist())
sel_row  = stocks_df[stocks_df["name"] == sel_name].iloc[0]
sel_code = sel_row["stock_code"]
is_pref  = int(sel_row.get("is_preferred", 0))
parent   = sel_row.get("parent_stock_code", "")
if is_pref and parent:
    st.caption(f"우선주 | 주가: {sel_code}  |  재무: 보통주({parent}) 기준")

fin_df = load_stock_data(sel_code)
if is_pref and parent and fin_df.empty:
    fin_df = load_stock_data(parent)

if fin_df.empty:
    st.warning("DB에 데이터가 없습니다.")
    st.stop()

years_available = sorted(fin_df["year"].unique())
st.caption(f"데이터: {min(years_available)}~{max(years_available)}년 | 총 {len(fin_df):,}개 항목")

st.divider()

# ── 1. 손익 분기 테이블 (가로 스크롤, 한눈에) ────────────
with st.expander("**손익계산서 (분기별)**", expanded=True):
    for item in INCOME_ITEMS:
        tbl = make_wide_table(fin_df, item)
        if tbl is None or tbl.dropna(how="all").empty:
            continue
        st.markdown(f"**{item}**")
        # 전체 연도를 한 번에 가로로 표시
        st.dataframe(
            tbl.style.format("{:,.1f}", na_rep="-"),
            use_container_width=True,
            height=105,
        )

# ── 2. 연간 그룹 ─────────────────────────────────────────
for group_name, items in ANNUAL_GROUPS.items():
    ann = fin_df[(fin_df["quarter"] == 0) & (fin_df["item"].isin(items))]
    if ann.empty:
        continue
    with st.expander(f"**{group_name}**", expanded=False):
        pivot = ann.pivot_table(index="item", columns="year", values="value", aggfunc="first")
        pivot = pivot.reindex([i for i in items if i in pivot.index])
        st.dataframe(
            pivot.style.format("{:,.2f}", na_rep="-"),
            use_container_width=True,
            height=min(60 + len(pivot) * 38, 420),
        )

st.divider()

# ── 3. 통합 그래프 (재무 + 주가 이중축) ──────────────────
st.subheader("분기 그래프 + 주가")

# 항목 옵션: 선호 항목 먼저
available_q = fin_df[fin_df["quarter"].isin([1,2,3,4])]["item"].unique().tolist()
preferred_available = [i for i in PREFERRED_ITEMS if i in available_q]
others = [i for i in sorted(available_q) if i not in preferred_available]
item_options = preferred_available + others

col1, col2 = st.columns([3, 1])
with col1:
    default_sel = [i for i in ["매출액", "영업이익", "순이익"] if i in item_options]
    graph_items = st.multiselect(
        "항목 선택 (여러 개 → 하나의 차트, 주가는 오른쪽 축)",
        options=item_options,
        default=default_sel,
    )
with col2:
    show_price = st.checkbox("주가 함께 보기", value=True)
    chart_type = st.radio("차트", ["바", "라인"], horizontal=True)

# 데이터 준비
pts_df = pd.DataFrame(make_quarter_series(fin_df, graph_items)) if graph_items else pd.DataFrame()
price_s = load_price_quarterly(sel_code) if show_price else None

if graph_items or (show_price and price_s is not None):
    fig = make_combined_fig(pts_df, graph_items, price_s, sel_name, chart_type)
    st.plotly_chart(fig, use_container_width=True)

    # ── PDF 다운로드 ──────────────────────────────────────
    st.divider()
    st.subheader("PDF 다운로드")

    # plotly-kaleido로 이미지 변환 후 HTML 기반 PDF 생성
    try:
        import kaleido  # noqa
        import base64

        # 그래프 이미지
        img_bytes = fig.to_image(format="png", width=1400, height=550, scale=1.5)
        img_b64 = base64.b64encode(img_bytes).decode()

        # 테이블 HTML
        tables_html = ""
        for item in INCOME_ITEMS:
            tbl = make_wide_table(fin_df, item)
            if tbl is None or tbl.dropna(how="all").empty:
                continue
            tables_html += f"<h3 style='margin:8px 0 4px'>{item}</h3>"
            tables_html += tbl.fillna("-").to_html(border=1, classes="tbl")

        html_content = f"""
        <html><head><meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; font-size: 10px; margin: 20px; color: #222; }}
            h1 {{ font-size: 18px; margin-bottom: 4px; }}
            h2 {{ font-size: 13px; margin: 16px 0 6px; border-bottom: 1px solid #ccc; }}
            h3 {{ font-size: 11px; color: #444; }}
            .tbl {{ border-collapse: collapse; width: 100%; margin-bottom: 8px; font-size: 9px; }}
            .tbl td, .tbl th {{ border: 1px solid #ddd; padding: 3px 6px; text-align: right; }}
            .tbl th {{ background: #f5f5f5; font-weight: bold; }}
        </style></head>
        <body>
        <h1>{sel_name} 재무 분석 리포트</h1>
        <h2>손익계산서 (분기별)</h2>
        {tables_html}
        <h2>분기 그래프 + 주가</h2>
        <img src="data:image/png;base64,{img_b64}" style="width:100%; margin-top:8px;"/>
        </body></html>
        """

        st.download_button(
            label="PDF 다운로드",
            data=html_content.encode("utf-8"),
            file_name=f"{sel_name}_재무분석.html",
            mime="text/html",
            help="다운로드 후 브라우저에서 열어 Ctrl+P → PDF로 저장하세요",
        )
        st.caption("다운로드된 HTML 파일을 브라우저로 열고 Ctrl+P → PDF로 저장하시면 돼요")

    except Exception as e:
        # kaleido 없으면 CSV만 제공
        st.info("그래프 포함 PDF는 kaleido 패키지가 필요합니다. 데이터 CSV를 다운로드하세요.")
        csv_data = fin_df[fin_df["quarter"] == 0].pivot_table(
            index="item", columns="year", values="value", aggfunc="first"
        )
        st.download_button(
            label="데이터 CSV 다운로드",
            data=csv_data.to_csv(encoding="utf-8-sig"),
            file_name=f"{sel_name}_재무데이터.csv",
            mime="text/csv",
        )
