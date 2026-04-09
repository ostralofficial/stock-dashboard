import streamlit as st

st.set_page_config(
    page_title="주식 재무 분석",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700;900&family=Space+Grotesk:wght@300;500;700&display=swap');

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1f3c 50%, #0a1628 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }

.hero-title {
    text-align: center;
    padding: 60px 0 20px;
    font-family: 'Space Grotesk', sans-serif;
}
.hero-title .icon { font-size: 64px; display: block; margin-bottom: 16px; }
.hero-title h1 {
    font-size: 52px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -1px;
    margin: 0;
}
.hero-title h1 span {
    background: linear-gradient(90deg, #0078ff, #00d4aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-title p {
    margin-top: 12px;
    font-size: 14px;
    color: rgba(255,255,255,0.35);
    letter-spacing: 4px;
    text-transform: uppercase;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 300;
}
.divline {
    width: 50px; height: 2px;
    background: linear-gradient(90deg, #0078ff, #00d4aa);
    margin: 20px auto 40px;
    border-radius: 2px;
}

.nav-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px;
    padding: 36px 28px;
    cursor: pointer;
    transition: all 0.3s ease;
    text-align: left;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.nav-card:hover {
    border-color: rgba(255,255,255,0.22);
    transform: translateY(-5px);
    box-shadow: 0 24px 48px rgba(0,0,0,0.5);
    background: rgba(255,255,255,0.07);
}
.nav-card .cicon { font-size: 36px; line-height: 1; }
.nav-card .ctitle {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    font-family: 'Noto Sans KR', sans-serif;
    margin: 0;
}
.nav-card .cdesc {
    font-size: 13px;
    color: rgba(255,255,255,0.38);
    line-height: 1.7;
    font-weight: 300;
    flex: 1;
}
.nav-card .carrow {
    color: rgba(255,255,255,0.2);
    font-size: 20px;
    align-self: flex-end;
    transition: all 0.3s;
}
.nav-card:hover .carrow { color: rgba(255,255,255,0.6); transform: translate(3px,-3px); }
.nav-card.coming { opacity: 0.45; cursor: default; }
.nav-card.coming:hover { transform: none; box-shadow: none; background: rgba(255,255,255,0.04); }
.badge {
    display: inline-block;
    font-size: 10px;
    padding: 2px 10px;
    border-radius: 20px;
    background: rgba(255,140,0,0.15);
    color: rgba(255,180,50,0.85);
    border: 1px solid rgba(255,140,0,0.25);
    font-weight: 500;
    letter-spacing: 1px;
}
.nav-card.blue  { border-top: 2px solid rgba(0,120,255,0.4); }
.nav-card.green { border-top: 2px solid rgba(0,212,170,0.4); }
.nav-card.purple{ border-top: 2px solid rgba(130,80,255,0.3); }
.nav-card.orange{ border-top: 2px solid rgba(255,140,0,0.4); }

/* 버튼 숨기기 */
div[data-testid="stButton"] button {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# ── 히어로 ───────────────────────────────────────────────
st.markdown("""
<div class="hero-title">
    <span class="icon">📈</span>
    <h1>주식 <span>재무분석</span></h1>
    <p>Financial Intelligence Platform</p>
</div>
<div class="divline"></div>
""", unsafe_allow_html=True)

# ── 카드 ─────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown("""
    <div class="nav-card blue" onclick="window.location.href='/종목_상세'">
        <div class="cicon">🔍</div>
        <div class="ctitle">종목 상세</div>
        <div class="cdesc">개별 종목의 분기별 재무 데이터와<br>주가 추이를 한눈에 확인</div>
        <div class="carrow">↗</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="nav-card green" onclick="window.location.href='/전체_랭킹'">
        <div class="cicon">📊</div>
        <div class="ctitle">전체 랭킹</div>
        <div class="cdesc">ROE, 영익률 등 항목별로<br>전체 종목을 정렬하여 비교</div>
        <div class="carrow">↗</div>
    </div>
    """, unsafe_allow_html=True)

col3, col4 = st.columns(2, gap="medium")

with col3:
    st.markdown("""
    <div class="nav-card purple coming">
        <div class="cicon">🌱</div>
        <div class="ctitle">Grow</div>
        <span class="badge">COMING SOON</span>
        <div class="cdesc">성장성 분석 및 투자 인사이트<br>— 준비 중입니다</div>
        <div class="carrow">↗</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="nav-card orange" onclick="window.location.href='/설정'">
        <div class="cicon">⚙️</div>
        <div class="ctitle">설정</div>
        <div class="cdesc">DART API 키 설정 및<br>데이터 수집 관리</div>
        <div class="carrow">↗</div>
    </div>
    """, unsafe_allow_html=True)

# ── 클릭 버튼 (실제 네비게이션용) ────────────────────────
st.markdown("<div style='margin-top: -180px;'>", unsafe_allow_html=True)
c1, c2 = st.columns(2, gap="medium")
with c1:
    if st.button("→ 종목 상세", key="b1", use_container_width=True):
        st.switch_page("pages/1_종목_상세.py")
with c2:
    if st.button("→ 전체 랭킹", key="b2", use_container_width=True):
        st.switch_page("pages/2_전체_랭킹.py")

c3, c4 = st.columns(2, gap="medium")
with c3:
    st.button("→ Grow (준비중)", key="b3", use_container_width=True, disabled=True)
with c4:
    if st.button("→ 설정", key="b4", use_container_width=True):
        st.switch_page("pages/3_설정.py")
st.markdown("</div>", unsafe_allow_html=True)
