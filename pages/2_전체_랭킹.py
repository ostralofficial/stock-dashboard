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
# 항목: (표시명, DB 저장명, 포맷타입)  포맷: pct=%, abs=절대값, x=배수
RANKING_ITEMS_META = [
    ("매출증가",      "매출증가",     "pct"),
    ("매출원가률",    "매출원가률",   "pct"),
    ("매출총이익률",  "매출총이익률", "pct"),
    ("영익증가",      "영익증가",     "pct"),
    ("영익률",        "영익률",       "pct"),
    ("순익증가",      "순익증가",     "pct"),
    ("순익률",        "순익률",       "pct"),
    ("배당성향",      "배당성향",     "pct"),
    ("배당수익률",    "배당수익률",   "pct"),
    ("ROE",           "ROE",          "pct"),
    ("ROE평균",       "ROE평균",      "pct"),
    ("ROIC",          "ROIC",         "pct"),
    ("부채비율",      "부채비율",     "abs"),
    ("주식소각비율",  "주식소각비율", "pct"),
    ("PER",           "PER",          "abs"),
    ("PBR",           "PBR",          "abs"),
    ("적정가격",      "적정가격",     "abs"),
    ("적정가격대비",  "적정가격대비", "pct"),
    ("RIM가격",       "RIM가격",      "abs"),
    ("기대수익률",    "기대수익률",   "pct"),
    ("서준식교수",    "서준식교수",   "abs"),
    ("10년가격",      "10년가격",     "abs"),
]
RANKING_ITEMS = [m[0] for m in RANKING_ITEMS_META]
ITEM_DB_NAME  = {m[0]: m[1] for m in RANKING_ITEMS_META}
ITEM_FORMAT   = {m[0]: m[2] for m in RANKING_ITEMS_META}
NON_PCT_ITEMS = {m[0] for m in RANKING_ITEMS_META if m[2] == "abs"}

@st.cache_data(ttl=300, show_spinner="데이터 로딩 중...")
def load_ranking_data(year, item):
    client = get_client()
    db_name = ITEM_DB_NAME.get(item, item)
    res = (client.table("financials")
           .select("stock_code, value")
           .eq("year", year)
           .eq("quarter", 0)
           .eq("item", db_name)
           .execute())
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    stocks = get_all_stocks()[["stock_code", "name"]]
    merged = df.merge(stocks, on="stock_code", how="left")[["name", "stock_code", "value"]]
    return merged[merged["value"].notna()]

@st.cache_data(ttl=300, show_spinner=False)
def load_price_map():
    """최신 주가 딕셔너리 {stock_code: close}"""
    try:
        client = get_client()
        stocks = get_all_stocks()[["stock_code"]]
        codes = stocks["stock_code"].tolist()
        price_map = {}
        for i in range(0, len(codes), 200):
            chunk = codes[i:i+200]
            res = (client.table("prices")
                   .select("stock_code, close, date")
                   .in_("stock_code", chunk)
                   .order("date", desc=True)
                   .execute())
            if res.data:
                seen = set()
                for r in res.data:
                    if r["stock_code"] not in seen:
                        price_map[r["stock_code"]] = r["close"]
                        seen.add(r["stock_code"])
        return price_map
    except Exception:
        return {}

def calc_realtime(item, base_df, year):
    """DB에 없는 계산 지표를 실시간으로 계산"""
    client = get_client()
    stocks = get_all_stocks()[["stock_code", "name"]]

    def fetch(it):
        res = (client.table("financials").select("stock_code, value")
               .eq("year", year).eq("quarter", 0).eq("item", it).execute())
        if not res.data:
            return {}
        return {r["stock_code"]: r["value"] for r in res.data}

    rows = []

    if item == "적정가격대비":
        price_map = load_price_map()
        apt = fetch("적정가격")
        for code, apt_val in apt.items():
            price = price_map.get(code)
            if price and apt_val and apt_val != 0:
                rows.append({"stock_code": code, "value": price / apt_val})

    elif item == "PER":
        price_map = load_price_map()
        eps = fetch("EPS_CALC")
        if not eps: eps = fetch("EPS")
        for code, eps_val in eps.items():
            price = price_map.get(code)
            if price and eps_val and eps_val > 0:
                rows.append({"stock_code": code, "value": price / eps_val})

    elif item == "PBR":
        price_map = load_price_map()
        bps = fetch("BPS_CALC")
        if not bps: bps = fetch("BPS")
        for code, bps_val in bps.items():
            price = price_map.get(code)
            if price and bps_val and bps_val > 0:
                rows.append({"stock_code": code, "value": price / bps_val})

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
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
REALTIME_ITEMS = {"적정가격대비", "PER", "PBR"}

with st.spinner("데이터 조회 중..."):
    if sel_item in REALTIME_ITEMS:
        rank_df = calc_realtime(sel_item, None, sel_year)
    else:
        rank_df = load_ranking_data(sel_year, sel_item)

if rank_df.empty:
    st.warning(f"{sel_year}년 '{sel_item}' 데이터가 없습니다. 지표 계산을 먼저 실행해주세요.")
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
    data=display_df.to_csv(index=True).encode("cp949", errors="replace"),
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
