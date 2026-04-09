import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(page_title="전체 랭킹", page_icon="📊", layout="wide")
st.header("전체 종목 랭킹")

XLSX_PATH = Path(__file__).parent.parent / "EPS-ACCUM.xlsx"

# simple 시트 항목 (컬럼 인덱스 기준)
SIMPLE_COLS = {
    "주가": 5, "PER": 6, "PBR": 7, "BPS": 8,
    "P/주당FCF": 9, "시가총액": 10, "시총대비현금": 11,
    "EV": 12, "EV/EBITDA": 13, "Ey": 14, "PEG": 15, "psr": 16,
    "적정주가": 17, "세법적정가%": 18, "RIM-기대수익": 19,
    "재고자산회전율": 20, "매출채권회전율": 21, "현금": 22,
    "부채비율": 24, "매출증가": 25, "해외매출증가": 26,
    "해외매출비중": 27, "매출원가증가": 28, "영익증가": 29,
    "영익률": 30, "순익증가": 31, "순익5년": 32,
    "EPS증가": 33, "순익률": 34, "배당수익률": 35,
    "배당증가": 36, "배당5년": 37, "배당성향": 38,
    "ROE": 39, "주식수": 40, "주식수변동/3y": 41,
    "NEFF": 42, "Div/per+Roe/per": 43, "Roe/pbr": 44,
    "서준식교수": 45, "52주최저가대비": 48, "ROE변동성": 50,
    "10년가치": 51, "10년가치승수": 52, "기대수익률": 53,
    "현재가대비": 55, "CAPM": 56, "현재가대비CAPM": 57,
}

@st.cache_data(ttl=600, show_spinner="simple 시트 로딩 중...")
def load_simple():
    if not XLSX_PATH.exists():
        return None
    raw = pd.read_excel(str(XLSX_PATH), sheet_name="simple", header=None)
    rows = []
    for _, r in raw.iloc[1:].iterrows():
        name = r.iloc[1]
        if pd.isna(name) or str(name).strip() == "":
            continue
        row = {"종목명": str(name).strip()}
        for col_name, ci in SIMPLE_COLS.items():
            try:
                row[col_name] = float(r.iloc[ci])
            except:
                row[col_name] = None
        rows.append(row)
    return pd.DataFrame(rows)

if not XLSX_PATH.exists():
    st.error("EPS-ACCUM.xlsx 파일이 stock_app 폴더에 있어야 합니다.")
    st.stop()

df = load_simple()
if df is None or df.empty:
    st.warning("데이터를 불러올 수 없습니다.")
    st.stop()

# ── 필터 & 정렬 ──────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    sel_col = st.selectbox("정렬 기준 항목", list(SIMPLE_COLS.keys()), index=list(SIMPLE_COLS.keys()).index("ROE"))
with col2:
    order = st.radio("정렬 방향", ["내림차순 (높은값→낮은값)", "오름차순 (낮은값→높은값)"], index=0)
with col3:
    top_n = st.selectbox("표시 개수", [30, 50, 100, 200, 0], format_func=lambda x: "전체" if x == 0 else f"상위 {x}개")

ascending = "오름차순" in order

sort_df = df[["종목명", sel_col]].dropna(subset=[sel_col]).copy()
sort_df = sort_df.sort_values(sel_col, ascending=ascending).reset_index(drop=True)
sort_df.index += 1  # 1부터 시작

if top_n > 0:
    sort_df = sort_df.head(top_n)

st.caption(f"총 {len(df)}개 종목 중 {len(sort_df)}개 표시 | NaN 제외")

# ── 숫자 포맷 판단 (% 항목은 % 표시) ─────────────────────
pct_cols = {"EPS증가", "매출증가", "영익증가", "순익증가", "배당증가",
            "ROE", "영익률", "순익률", "배당수익률", "배당성향",
            "Ey", "RIM-기대수익", "기대수익률", "CAPM", "해외매출비중",
            "시총대비현금", "세법적정가%", "현재가대비", "현재가대비CAPM",
            "Roe/pbr", "ROE변동성"}

if sel_col in pct_cols:
    fmt = "{:.2%}"
    sort_df[sel_col] = sort_df[sel_col]
    display_df = sort_df.style.format({sel_col: lambda x: f"{x:.1%}"}, na_rep="-")
else:
    display_df = sort_df.style.format({sel_col: "{:,.2f}"}, na_rep="-")

# ── 테이블 ───────────────────────────────────────────────
st.dataframe(display_df, use_container_width=True, height=500)

st.download_button(
    "CSV 다운로드",
    data=sort_df.to_csv(encoding="utf-8-sig", index=True),
    file_name=f"ranking_{sel_col}.csv",
    mime="text/csv",
)

# ── 바 차트 (상위 30개) ──────────────────────────────────
st.divider()
chart_n = min(30, len(sort_df))
chart_df = sort_df.head(chart_n).copy()

fig = px.bar(
    chart_df,
    x="종목명", y=sel_col,
    title=f"{sel_col} {'상위' if not ascending else '하위'} {chart_n}개",
    color=sel_col,
    color_continuous_scale="Blues" if not ascending else "Reds_r",
)
fig.update_layout(
    height=420,
    xaxis_tickangle=-45,
    coloraxis_showscale=False,
    margin=dict(b=100),
)
st.plotly_chart(fig, use_container_width=True)
