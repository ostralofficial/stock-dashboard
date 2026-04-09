import streamlit as st

st.set_page_config(
    page_title="Ostral",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&family=Space+Grotesk:wght@300;500;700&display=swap');

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1f3c 50%, #0a1628 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }

.hero-title {
    text-align: center;
    padding: 60px 0 10px;
    font-family: 'Space Grotesk', sans-serif;
}
.hero-title .icon { font-size: 60px; display: block; margin-bottom: 12px; }
.hero-title h1 {
    font-size: 58px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -2px;
    margin: 0;
    background: linear-gradient(90deg, #0078ff, #00d4aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-title p {
    margin-top: 10px;
    font-size: 13px;
    color: rgba(255,255,255,0.3);
    letter-spacing: 4px;
    text-transform: uppercase;
    font-weight: 300;
}
.divline {
    width: 50px; height: 2px;
    background: linear-gradient(90deg, #0078ff, #00d4aa);
    margin: 18px auto 36px;
    border-radius: 2px;
}

/* 카드 버튼 스타일 */
div[data-testid="stButton"] > button {
    width: 100% !important;
    min-height: 200px !important;
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 20px !important;
    color: white !important;
    font-family: 'Noto Sans KR', sans-serif !important;
    transition: all 0.3s ease !important;
    padding: 32px 28px !important;
    text-align: left !important;
    white-space: pre-wrap !important;
    line-height: 1.6 !important;
    cursor: pointer !important;
}
div[data-testid="stButton"] > button:hover {
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.22) !important;
    transform: translateY(-4px) !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.4) !important;
}
div[data-testid="stButton"] > button:disabled {
    opacity: 0.4 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* 각 카드 상단 색상 */
div[data-testid="stButton"]:nth-of-type(1) > button { border-top: 2px solid rgba(0,120,255,0.5) !important; }
div[data-testid="stButton"]:nth-of-type(2) > button { border-top: 2px solid rgba(0,212,170,0.5) !important; }
div[data-testid="stButton"]:nth-of-type(3) > button { border-top: 2px solid rgba(130,80,255,0.4) !important; }
div[data-testid="stButton"]:nth-of-type(4) > button { border-top: 2px solid rgba(255,140,0,0.5) !important; }
</style>
""", unsafe_allow_html=True)

# ── 히어로 ───────────────────────────────────────────────
st.markdown("""
<div class="hero-title">
    <span class="icon">📈</span>
    <h1>Ostral</h1>
    <p>Financial Intelligence Platform</p>
</div>
<div class="divline"></div>
""", unsafe_allow_html=True)

# ── 카드 버튼 ─────────────────────────────────────────────
col1, col2 = st.columns(2, gap="medium")

with col1:
    if st.button(
        "🔍\n\n종목 상세\n\n개별 종목의 분기별 재무 데이터와\n주가 추이를 한눈에 확인\n\n↗",
        key="btn_stock",
        use_container_width=True,
    ):
        st.switch_page("pages/1_종목_상세.py")

with col2:
    if st.button(
        "📊\n\n전체 랭킹\n\nROE, 영익률 등 항목별로\n전체 종목을 정렬하여 비교\n\n↗",
        key="btn_rank",
        use_container_width=True,
    ):
        st.switch_page("pages/2_전체_랭킹.py")

col3, col4 = st.columns(2, gap="medium")

with col3:
    st.button(
        "🌱\n\nGrow  — COMING SOON\n\n성장성 분석 및 투자 인사이트\n준비 중입니다\n\n↗",
        key="btn_grow",
        use_container_width=True,
        disabled=True,
    )

with col4:
    if st.button(
        "⚙️\n\n설정\n\nDART API 키 설정 및\n데이터 수집 관리\n\n↗",
        key="btn_setting",
        use_container_width=True,
    ):
        st.switch_page("pages/3_설정.py")
