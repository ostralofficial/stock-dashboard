import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks, get_client

st.set_page_config(page_title="전체 랭킹", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
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
    transition: all 0.2s !important;
}
.home-btn button:hover {
    background: rgba(255,255,255,0.15) !important;
    color: #fff !important;
}
</style>
""", unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="home-btn">', unsafe_allow_html=True)
    if st.button("← Home"):
        st.switch_page("app.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.header("전체 종목 랭킹")

# 랭킹에 사용할 연간(quarter=0) 항목들
RANKING_ITEMS = [
    "매출증가", "매출원가증가", "매출원가률",
    "매출총이익률", "판관비증가", "판관비율",
    "영익증가", "영익률",
    "순익증가", "순익률",
    "EPS증가", "배당증가", "배당성향", "배당수익률",
    "ROE", "ROE평균",
    "부채비율", "주식수변동",
    "PER", "PBR", "EV/EBITDA", "Ey", "psr",
    "적정가격", "RIM가격", "기대수익률", "10년가격",
]

# % 표시 제외 항목 (절대값/배수)
NON_PCT_ITEMS = {"주식수변동", "Ey", "적정가격", "RIM가격", "psr", "PER", "PBR", "EV/EBITDA", "10년가격"}

@st.cache_data(ttl=300, show_spinner="데이터 로딩 중...")
def load_ranking_data(year, item):
    client = get_client()
    res = (client.table("financials")
           .select("stock_code, value")
           .eq("year", year)
           .eq("quarter", 0)
           .eq("item", item)
           .execute())
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    stocks = get_all_stocks()[["stock_code", "name"]]
    merged = df.merge(stocks, on="stock_code", how="left")[["name", "stock_code", "value"]]
    return merged[merged["value"].notna()]

@st.cache_data(ttl=600, show_spinner="종목 목록 로딩 중...")
def get_available_years():
    client = get_client()
    res = client.table("financials").select("year").order("year", desc=True).limit(1).execute()
    if not res.data:
        return list(range(2025, 2013, -1))
    max_year = int(res.data[0]["year"])
    return list(range(max_year, 2013, -1))

# ── 필터 ─────────────────────────────────────────────────
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    sel_item = st.selectbox("정렬 기준 항목", RANKING_ITEMS, index=RANKING_ITEMS.index("ROE"))
with col2:
    order = st.radio("정렬", ["내림차순", "오름차순"], horizontal=True)
with col3:
    top_n = st.selectbox("표시 개수", [30, 50, 100, 200, 0],
                         format_func=lambda x: "전체" if x == 0 else f"상위 {x}개")

# 최신 연도 자동 선택
years = get_available_years()
sel_year = years[0] if years else 2025

ascending = order == "오름차순"

# ── 데이터 로드 & 정렬 ────────────────────────────────────
with st.spinner("데이터 조회 중..."):
    rank_df = load_ranking_data(sel_year, sel_item)

if rank_df.empty:
    st.warning(f"{sel_year}년 '{sel_item}' 데이터가 없습니다.")
    st.stop()

# NaN 및 None 제거 (이미 dropna 했지만 혹시 모를 케이스 대비)
rank_df = rank_df[rank_df["value"].notna()]
rank_df = rank_df.sort_values("value", ascending=ascending).reset_index(drop=True)
rank_df.index += 1
rank_df.columns = ["종목명", "종목코드", sel_item]

# 마이너스 값 제외 옵션
hide_negative = st.checkbox("마이너스 값 종목 제외", value=True)
if hide_negative:
    rank_df = rank_df[rank_df[sel_item] >= 0]

if top_n > 0:
    display_df = rank_df.head(top_n)
else:
    display_df = rank_df

st.caption(f"기준 연도: {sel_year}년 (최신) | 총 {len(rank_df)}개 종목 중 {len(display_df)}개 표시")

# ── 테이블 ────────────────────────────────────────────────
st.dataframe(
    display_df.style.format(
        {sel_item: "{:,.2f}" if sel_item in NON_PCT_ITEMS else "{:.1%}"},
        na_rep="-"
    ),
    use_container_width=True,
    height=500,
)

st.download_button(
    "CSV 다운로드",
    data=display_df.to_csv(encoding="utf-8-sig", index=True),
    file_name=f"랭킹_{sel_year}_{sel_item}.csv",
    mime="text/csv",
)

# ── 바 차트 (상위 30개) ───────────────────────────────────
st.divider()
chart_n = min(30, len(display_df))
chart_df = display_df.head(chart_n).copy()

y_vals = chart_df[sel_item] if sel_item in NON_PCT_ITEMS else chart_df[sel_item] * 100
chart_plot = chart_df.copy()
chart_plot["_y"] = y_vals
y_label = sel_item if sel_item in NON_PCT_ITEMS else f"{sel_item} (%)"

fig = px.bar(
    chart_plot,
    x="종목명", y="_y",
    title=f"{sel_year}년 {sel_item} {'상위' if not ascending else '하위'} {chart_n}개",
    color="_y",
    color_continuous_scale="Blues" if not ascending else "Reds_r",
    labels={"_y": y_label},
)
fig.update_layout(
    height=450,
    xaxis_tickangle=-45,
    coloraxis_showscale=False,
    margin=dict(b=120),
)
st.plotly_chart(fig, use_container_width=True)
