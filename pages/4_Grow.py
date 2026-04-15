import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks, get_client

st.set_page_config(page_title="Grow", page_icon="🌱", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
.home-btn button {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: rgba(255,255,255,0.8) !important;
    border-radius: 8px !important;
    padding: 4px 14px !important;
    font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="home-btn">', unsafe_allow_html=True)
    if st.button("← Home"):
        st.switch_page("app.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.header("Grow")

client = get_client()

# ── Grow 종목 목록 DB 조작 함수 ───────────────────────────
def get_grow_stocks():
    try:
        res = client.table("grow_watchlist").select("stock_code, added_at").order("added_at").execute()
        return [r["stock_code"] for r in (res.data or [])]
    except Exception:
        return []

def add_grow_stock(stock_code):
    try:
        client.table("grow_watchlist").upsert(
            {"stock_code": stock_code},
            on_conflict="stock_code"
        ).execute()
        return True
    except Exception as e:
        st.error(f"추가 실패: {e}")
        return False

def remove_grow_stock(stock_code):
    try:
        client.table("grow_watchlist").delete().eq("stock_code", stock_code).execute()
        return True
    except Exception:
        return False

# ── 재무 데이터 로드 ──────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_financials(stock_code):
    res = (client.table("financials")
           .select("year, quarter, item, value")
           .eq("stock_code", stock_code)
           .eq("quarter", 0)
           .in_("item", ["BPS", "BPS_CALC", "EPS", "EPS_CALC", "DPS",
                         "순이익률", "ROE", "ROIC", "순익률"])
           .order("year")
           .execute())
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def make_pivot(df, items, n_years=10):
    if df.empty:
        return pd.DataFrame()
    # BPS_CALC → BPS 로 통합
    df = df.copy()
    df["item"] = df["item"].replace({"BPS_CALC": "BPS", "EPS_CALC": "EPS", "순익률": "순이익률"})
    pivot = df[df["item"].isin(items)].pivot_table(
        index="item", columns="year", values="value", aggfunc="first"
    )
    pivot = pivot.reindex([i for i in items if i in pivot.index])
    # 최근 n_years
    cols = sorted(pivot.columns)[-n_years:]
    return pivot[cols]

# ── PDF/CSV 다운로드 ──────────────────────────────────────
def make_download(name, pivot, fig_bar, fig_line):
    try:
        import base64
        tables_html = pivot.fillna("-").to_html(border=1, classes="tbl")
        img_bar = base64.b64encode(fig_bar.to_image(format="png", width=1200, height=400)).decode()
        img_line = base64.b64encode(fig_line.to_image(format="png", width=1200, height=400)).decode()
        html = f"""<html><head><meta charset="utf-8">
        <style>body{{font-family:Arial,sans-serif;font-size:11px;margin:20px}}
        h1{{font-size:18px}} h2{{font-size:14px;margin-top:16px}}
        .tbl{{border-collapse:collapse;width:100%}}
        .tbl td,.tbl th{{border:1px solid #ccc;padding:4px 8px;text-align:right}}
        .tbl th{{background:#f5f5f5}}</style></head><body>
        <h1>{name} — 성장 분석</h1>
        <h2>최근 10년 주요 지표</h2>{tables_html}
        <h2>BPS / EPS / DPS 추이</h2>
        <img src="data:image/png;base64,{img_bar}" style="width:100%"/>
        <h2>ROE / ROIC / 순이익률 추이</h2>
        <img src="data:image/png;base64,{img_line}" style="width:100%"/>
        </body></html>"""
        return html.encode("utf-8")
    except Exception:
        return None

# ── 종목 추가 UI ─────────────────────────────────────────
all_stocks = get_all_stocks()
grow_codes = get_grow_stocks()

with st.expander("➕ 종목 추가", expanded=False):
    if all_stocks.empty:
        st.info("종목을 먼저 설정에서 추가해주세요")
    else:
        search = st.text_input("종목 검색", placeholder="삼성, 카카오...", key="grow_search")
        filtered = all_stocks.copy()
        if search:
            filtered = filtered[filtered["name"].str.contains(search, na=False)]

        already = set(grow_codes)
        add_targets = filtered[~filtered["stock_code"].isin(already)]

        if add_targets.empty:
            st.caption("검색 결과 없음 또는 이미 모두 추가됨")
        else:
            st.caption(f"{len(add_targets)}개 종목")
            cols_per_row = 4
            rows = [add_targets.iloc[i:i+cols_per_row] for i in range(0, len(add_targets), cols_per_row)]
            for row_df in rows:
                cols = st.columns(cols_per_row)
                for j, (_, r) in enumerate(row_df.iterrows()):
                    with cols[j]:
                        if st.checkbox(r["name"], key=f"chk_{r['stock_code']}"):
                            if add_grow_stock(r["stock_code"]):
                                st.rerun()

st.divider()

# ── Grow 종목 목록 표시 ───────────────────────────────────
if not grow_codes:
    st.info("위의 '종목 추가' 버튼으로 관심 종목을 추가해보세요!")
    st.stop()

grow_df = all_stocks[all_stocks["stock_code"].isin(grow_codes)].copy()

TABLE_ITEMS = ["BPS", "EPS", "DPS", "순이익률", "ROE", "ROIC"]
BAR_ITEMS   = ["BPS", "EPS", "DPS"]
LINE_ITEMS  = ["ROE", "ROIC", "순이익률"]

for _, stock_row in grow_df.iterrows():
    code = stock_row["stock_code"]
    name = stock_row["name"]

    col_name, col_detail, col_dl, col_del = st.columns([4, 1.2, 1, 0.7])
    with col_name:
        st.markdown(f"### {name}")
    with col_detail:
        if st.button("종목 상세 →", key=f"detail_{code}"):
            st.session_state["detail_stock"] = name
            st.switch_page("pages/1_종목_상세.py")
    with col_dl:
        dl_placeholder = st.empty()
    with col_del:
        if st.button("✕ 삭제", key=f"del_{code}"):
            remove_grow_stock(code)
            st.rerun()

    with st.expander(f"▼ {name} 상세 보기", expanded=False):
        fin_df = load_financials(code)

        if fin_df.empty:
            st.warning("재무 데이터가 없습니다. DART 수집 후 지표 계산을 실행해주세요.")
            continue

        # 1. 테이블
        st.markdown("**최근 10년 주요 지표**")
        pivot = make_pivot(fin_df, TABLE_ITEMS, n_years=10)
        if not pivot.empty:
            fmt = {}
            for item in pivot.index:
                if item in ["ROE", "ROIC", "순이익률"]:
                    fmt[item] = lambda x: f"{x*100:.1f}%" if pd.notna(x) else "-"
                else:
                    fmt[item] = lambda x: f"{x:,.0f}" if pd.notna(x) else "-"
            st.dataframe(
                pivot.style.format(
                    {col: "{:,.0f}" for col in pivot.columns},
                    na_rep="-"
                ),
                use_container_width=True,
            )

        # 2. 막대그래프 - BPS, EPS, DPS
        bar_pivot = make_pivot(fin_df, BAR_ITEMS, n_years=10)
        fig_bar = go.Figure()
        colors = {"BPS": "#378ADD", "EPS": "#1D9E75", "DPS": "#EF9F27"}
        if not bar_pivot.empty:
            years = [str(y) for y in bar_pivot.columns]
            for item in BAR_ITEMS:
                if item in bar_pivot.index:
                    fig_bar.add_trace(go.Bar(
                        name=item,
                        x=years,
                        y=bar_pivot.loc[item].values,
                        marker_color=colors.get(item, "#888"),
                    ))
        fig_bar.update_layout(
            title="BPS / EPS / DPS 추이",
            barmode="group",
            height=360,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=60, b=40),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # 3. 선그래프 - ROE, ROIC, 순이익률 (+ 보조축 없음, % 단위)
        line_pivot = make_pivot(fin_df, LINE_ITEMS, n_years=10)
        fig_line = go.Figure()
        lcolors = {"ROE": "#D85A30", "ROIC": "#534AB7", "순이익률": "#1D9E75"}
        if not line_pivot.empty:
            years_l = [str(y) for y in line_pivot.columns]
            for item in LINE_ITEMS:
                if item in line_pivot.index:
                    fig_line.add_trace(go.Scatter(
                        name=item,
                        x=years_l,
                        y=(line_pivot.loc[item].values * 100).round(2),
                        mode="lines+markers",
                        line=dict(width=2, color=lcolors.get(item, "#888")),
                    ))
        fig_line.update_layout(
            title="ROE / ROIC / 순이익률 추이 (%)",
            height=360,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            yaxis=dict(ticksuffix="%"),
            margin=dict(t=60, b=40),
        )
        st.plotly_chart(fig_line, use_container_width=True)

        # 다운로드 버튼
        dl_data = make_download(name, pivot, fig_bar, fig_line)
        if dl_data:
            dl_placeholder.download_button(
                "⬇ 다운로드",
                data=dl_data,
                file_name=f"{name}_grow.html",
                mime="text/html",
                key=f"dl_{code}",
            )

    st.divider()
