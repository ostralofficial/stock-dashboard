import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks

st.set_page_config(page_title="52 Week", page_icon="📅", layout="wide", initial_sidebar_state="collapsed")
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

st.header("52 Week")

# ── 데이터 로드 ───────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="52주 데이터 로딩 중...")
def load_52week_data():
    stocks = get_all_stocks()
    if stocks.empty:
        return pd.DataFrame()

    end = datetime.today()
    start = end - timedelta(weeks=52)
    end_str   = end.strftime("%Y-%m-%d")
    start_str = start.strftime("%Y-%m-%d")

    rows = []
    progress = st.progress(0)
    status = st.empty()
    total = len(stocks)

    for i, (_, row) in enumerate(stocks.iterrows()):
        progress.progress((i + 1) / total)
        status.text(f"조회 중: {row['name']} ({i+1}/{total})")
        try:
            df = fdr.DataReader(row["stock_code"], start_str, end_str)
            if df is None or df.empty or len(df) < 20:
                continue
            high_52  = df["High"].max()
            low_52   = df["Low"].min()
            close_now = float(df["Close"].iloc[-1])
            close_1y  = float(df["Close"].iloc[0])

            ret_52 = (close_now - close_1y) / close_1y if close_1y != 0 else None
            pct_from_high = (close_now - high_52) / high_52 if high_52 != 0 else None
            pct_from_low  = (close_now - low_52)  / low_52  if low_52  != 0 else None

            rows.append({
                "stock_code": row["stock_code"],
                "종목명": row["name"],
                "현재가": close_now,
                "52주최고": high_52,
                "52주최저": low_52,
                "52주수익률": ret_52,
                "고가대비": pct_from_high,
                "저가대비": pct_from_low,
            })
        except Exception:
            continue

    progress.empty()
    status.empty()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── 새로고침 버튼 ─────────────────────────────────────────
col_h, col_btn = st.columns([6, 1])
with col_h:
    st.caption(f"기준일: {datetime.today().strftime('%Y-%m-%d')} | 데이터는 1시간 캐시")
with col_btn:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

df_52 = load_52week_data()

if df_52.empty:
    st.warning("데이터를 불러올 수 없습니다. 종목을 먼저 추가해주세요.")
    st.stop()

# 종목상세 이동 헬퍼
def detail_btn(stock_code, name, key):
    if st.button("상세 →", key=key):
        st.session_state["detail_stock"] = name
        st.switch_page("pages/1_종목_상세.py")

# ── 1. 52주 최고가 근접 종목 ─────────────────────────────
st.subheader("52주 최고가 근접 종목")
st.caption("현재가가 52주 최고가에 가까운 순 (고가대비 하락폭이 작은 순)")

high_df = (df_52.dropna(subset=["고가대비"])
           .sort_values("고가대비", ascending=False)
           .reset_index(drop=True))
high_df.index += 1

display_high = high_df[["종목명", "현재가", "52주최고", "고가대비", "52주수익률"]].copy()
display_high.columns = ["종목명", "현재가", "52주최고", "고가대비(%)", "52주수익률(%)"]
display_high["고가대비(%)"] = (display_high["고가대비(%)"] * 100).round(1)
display_high["52주수익률(%)"] = (display_high["52주수익률(%)"] * 100).round(1)
display_high["현재가"] = display_high["현재가"].map("{:,.0f}".format)
display_high["52주최고"] = display_high["52주최고"].map("{:,.0f}".format)

st.dataframe(
    display_high.style.background_gradient(subset=["고가대비(%)"], cmap="Blues"),
    use_container_width=True,
    height=450,
)

# 종목 선택 → 상세 이동
sel_high = st.selectbox(
    "종목 선택 후 상세 보기",
    ["선택하세요"] + high_df["종목명"].tolist(),
    key="sel_high"
)
if sel_high != "선택하세요":
    row = high_df[high_df["종목명"] == sel_high].iloc[0]
    detail_btn(row["stock_code"], sel_high, key="btn_high_detail")

st.divider()

# ── 2. 52주 최저가 근접 종목 ─────────────────────────────
st.subheader("52주 최저가 근접 종목")
st.caption("현재가가 52주 최저가에 가까운 순 (저가대비 상승폭이 작은 순)")

low_df = (df_52.dropna(subset=["저가대비"])
          .sort_values("저가대비", ascending=True)
          .reset_index(drop=True))
low_df.index += 1

display_low = low_df[["종목명", "현재가", "52주최저", "저가대비", "52주수익률"]].copy()
display_low.columns = ["종목명", "현재가", "52주최저", "저가대비(%)", "52주수익률(%)"]
display_low["저가대비(%)"] = (display_low["저가대비(%)"] * 100).round(1)
display_low["52주수익률(%)"] = (display_low["52주수익률(%)"] * 100).round(1)
display_low["현재가"] = display_low["현재가"].map("{:,.0f}".format)
display_low["52주최저"] = display_low["52주최저"].map("{:,.0f}".format)

st.dataframe(
    display_low.style.background_gradient(subset=["저가대비(%)"], cmap="Reds_r"),
    use_container_width=True,
    height=450,
)

sel_low = st.selectbox(
    "종목 선택 후 상세 보기",
    ["선택하세요"] + low_df["종목명"].tolist(),
    key="sel_low"
)
if sel_low != "선택하세요":
    row = low_df[low_df["종목명"] == sel_low].iloc[0]
    detail_btn(row["stock_code"], sel_low, key="btn_low_detail")
