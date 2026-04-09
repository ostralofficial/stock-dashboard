import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks, get_conn

st.set_page_config(page_title="종목 상세", page_icon="🔍", layout="wide")
st.header("종목 상세")

# 손익 분기 항목 정의
INCOME_ITEMS = ["매출액", "매출원가", "매출총이익", "판관비", "영업이익", "순이익", "EPS"]

# 연간 그룹
ANNUAL_GROUPS = {
    "재무상태표": ["자산총계", "자본총계", "부채비율", "현금성자산", "매출채권", "재고자산", "단기차입금"],
    "현금흐름":   ["CFO", "주당CFO", "투자활동CF", "재무활동CF", "FCF", "주당FCF", "감가상각", "EBITDA", "현금증감"],
    "주주가치":   ["EPS", "EPS증가", "BPS", "DPS", "배당증가", "배당성향", "배당총액", "ROE", "ROE평균", "주식수"],
    "밸류에이션": ["PER", "PBR", "EV/EBITDA", "Ey", "psr", "적정가격", "RIM가격", "기대수익률", "10년가격"],
}

@st.cache_data(ttl=300, show_spinner="데이터 로딩 중...")
def load_stock_data(stock_code):
    conn = get_conn()
    df = pd.read_sql("""
        SELECT year, quarter, item, value
        FROM financials
        WHERE stock_code = ?
        ORDER BY year, quarter, item
    """, conn, params=(stock_code,))
    conn.close()
    return df

def make_quarter_table(df, item):
    """항목 하나 → 연도×분기 테이블"""
    sub = df[df["item"] == item].copy()
    if sub.empty:
        return None
    sub = sub[sub["quarter"].isin([0,1,2,3,4])]
    q_map = {0:"연간", 1:"1Q", 2:"2Q", 3:"3Q", 4:"4Q"}
    sub["분기"] = sub["quarter"].map(q_map)
    pivot = sub.pivot_table(index="분기", columns="year", values="value", aggfunc="first")
    # 행 순서 고정
    row_order = ["1Q", "2Q", "3Q", "4Q", "연간"]
    pivot = pivot.reindex([r for r in row_order if r in pivot.index])
    return pivot

def make_quarter_series(df, items):
    """여러 항목의 분기 시계열 → plotly용 리스트"""
    points = []
    sub = df[df["item"].isin(items) & df["quarter"].isin([1,2,3,4])]
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

# DB에서 이 종목 데이터 로드
fin_df = load_stock_data(sel_code)

# 우선주면 보통주 코드로 재무 조회
if is_pref and parent and fin_df.empty:
    fin_df = load_stock_data(parent)

if fin_df.empty:
    st.warning("DB에 데이터가 없습니다. '데이터 수집' 또는 이관 스크립트를 먼저 실행해주세요.")
    st.stop()

years_available = sorted(fin_df["year"].unique())
st.caption(f"데이터: {min(years_available)}~{max(years_available)}년 | 총 {len(fin_df):,}개 항목")

st.divider()

# ── 1. 손익 분기 테이블 ───────────────────────────────────
with st.expander("**손익계산서 (분기별)**", expanded=True):
    for item in INCOME_ITEMS:
        tbl = make_quarter_table(fin_df, item)
        if tbl is None or tbl.dropna(how="all").empty:
            continue
        st.markdown(f"**{item}**")
        st.dataframe(
            tbl.style.format("{:,.1f}", na_rep="-"),
            use_container_width=True,
            height=105,
        )

# ── 2. 연간 그룹 ─────────────────────────────────────────
for group_name, items in ANNUAL_GROUPS.items():
    # 연간(quarter=0) 데이터만
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

# ── 3. 분기 그래프 ────────────────────────────────────────
st.subheader("분기 그래프")

col1, col2 = st.columns([3, 1])
with col1:
    # DB에 실제로 있는 분기 항목만 옵션으로
    available_items = fin_df[fin_df["quarter"].isin([1,2,3,4])]["item"].unique().tolist()
    default_sel = [i for i in ["매출액","영업이익","순이익"] if i in available_items]
    graph_items = st.multiselect(
        "항목 선택 (여러 개 → 하나의 차트에 표시)",
        options=sorted(available_items),
        default=default_sel,
    )
with col2:
    show_price = st.checkbox("주가 함께 보기", value=True)
    chart_type = st.radio("차트", ["바", "라인"], horizontal=True)

if graph_items:
    points = make_quarter_series(fin_df, graph_items)
    if points:
        pts_df = pd.DataFrame(points)
        all_periods = sorted(pts_df["기간"].unique())

        fig = go.Figure()
        for item in graph_items:
            sub = pts_df[pts_df["항목"] == item].sort_values("기간")
            if sub.empty:
                continue
            if chart_type == "바":
                fig.add_trace(go.Bar(x=sub["기간"], y=sub["값"], name=item))
            else:
                fig.add_trace(go.Scatter(
                    x=sub["기간"], y=sub["값"],
                    mode="lines+markers", name=item, line=dict(width=2),
                ))

        fig.update_layout(
            title=f"{sel_name} — 분기별",
            xaxis=dict(tickangle=-45, tickvals=all_periods[::4]),
            barmode="group",
            hovermode="x unified",
            height=430,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(b=80),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── 4. 주가 (분기 말) ─────────────────────────────────────
if show_price:
    price_s = load_price_quarterly(sel_code)
    if price_s is not None and not price_s.empty:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=price_s.index, y=price_s.values,
            mode="lines+markers", name="주가(분기말)",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy", fillcolor="rgba(31,119,180,0.08)",
        ))
        fig2.update_layout(
            title=f"{sel_name} 주가 (분기 말 기준)",
            xaxis=dict(tickangle=-45),
            yaxis_title="원",
            height=330,
            hovermode="x unified",
            margin=dict(t=40, b=80),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("주가 로딩 실패 — FinanceDataReader가 설치되어 있어야 합니다")
