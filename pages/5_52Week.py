import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks, get_client

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

@st.cache_data(ttl=1800, show_spinner="데이터 로딩 중...")
def load_52week_from_db():
    client = get_client()
    # 가장 최신 날짜 조회
    res_date = (client.table("week52")
                .select("date")
                .order("date", desc=True)
                .limit(1)
                .execute())
    if not res_date.data:
        return pd.DataFrame(), None

    latest_date = res_date.data[0]["date"]

    res = (client.table("week52")
           .select("stock_code, name, close, high_52, low_52, return_52, pct_from_high, pct_from_low")
           .eq("date", latest_date)
           .execute())

    if not res.data:
        return pd.DataFrame(), latest_date

    df = pd.DataFrame(res.data)
    df.columns = ["종목코드", "종목명", "현재가", "52주최고", "52주최저",
                  "52주수익률", "고가대비", "저가대비"]
    return df, latest_date

# ── 헤더 & 새로고침 ───────────────────────────────────────
df_52, latest_date = load_52week_from_db()

col_h, col_btn = st.columns([6, 1])
with col_h:
    if latest_date:
        st.caption(f"기준일: {latest_date} | 매일 15:00 자동 업데이트 | 30분 캐시")
    else:
        st.caption("데이터 없음 — GitHub Actions가 아직 실행되지 않았을 수 있어요")
with col_btn:
    if st.button("🔄 새로고침"):
        st.cache_data.clear()
        st.rerun()

if df_52.empty:
    st.warning("52주 데이터가 없습니다.")
    st.info("GitHub Actions가 설정되면 매일 15시에 자동으로 데이터가 쌓여요.\n수동으로 실행하려면 GitHub → Actions → Update 52Week Data → Run workflow를 클릭하세요.")
    st.stop()

# 종목상세 이동
def go_detail(name):
    st.session_state["detail_stock"] = name
    st.switch_page("pages/1_종목_상세.py")

# ── 1. 52주 최고가 근접 종목 ─────────────────────────────
st.subheader("52주 최고가 근접 종목")
st.caption("현재가가 52주 최고가에 가까운 순")

high_df = (df_52.dropna(subset=["고가대비"])
           .sort_values("고가대비", ascending=False)
           .reset_index(drop=True))
high_df.index += 1

display_high = high_df[["종목명", "현재가", "52주최고", "고가대비", "52주수익률"]].copy()
display_high["고가대비(%)"] = (display_high["고가대비"] * 100).round(1)
display_high["52주수익률(%)"] = (display_high["52주수익률"] * 100).round(1)
display_high["현재가"] = display_high["현재가"].map("{:,.0f}".format)
display_high["52주최고"] = display_high["52주최고"].map("{:,.0f}".format)
display_high = display_high[["종목명", "현재가", "52주최고", "고가대비(%)", "52주수익률(%)"]]

st.dataframe(
    display_high.style.background_gradient(subset=["고가대비(%)"], cmap="Blues"),
    use_container_width=True,
    height=450,
)

sel_high = st.selectbox(
    "종목 선택 후 상세 보기",
    ["선택하세요"] + high_df["종목명"].tolist(),
    key="sel_high"
)
if sel_high != "선택하세요":
    if st.button("종목 상세 →", key="btn_high"):
        go_detail(sel_high)

st.divider()

# ── 2. 52주 최저가 근접 종목 ─────────────────────────────
st.subheader("52주 최저가 근접 종목")
st.caption("현재가가 52주 최저가에 가까운 순")

low_df = (df_52.dropna(subset=["저가대비"])
          .sort_values("저가대비", ascending=True)
          .reset_index(drop=True))
low_df.index += 1

display_low = low_df[["종목명", "현재가", "52주최저", "저가대비", "52주수익률"]].copy()
display_low["저가대비(%)"] = (display_low["저가대비"] * 100).round(1)
display_low["52주수익률(%)"] = (display_low["52주수익률"] * 100).round(1)
display_low["현재가"] = display_low["현재가"].map("{:,.0f}".format)
display_low["52주최저"] = display_low["52주최저"].map("{:,.0f}".format)
display_low = display_low[["종목명", "현재가", "52주최저", "저가대비(%)", "52주수익률(%)"]]

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
    if st.button("종목 상세 →", key="btn_low"):
        go_detail(sel_low)
