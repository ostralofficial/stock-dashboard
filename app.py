import streamlit as st

st.set_page_config(
    page_title="주식 재무 분석",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700;900&family=Space+Grotesk:wght@300;400;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

.main > div { padding: 0 !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }

body {
    background: #0a0e1a;
    font-family: 'Noto Sans KR', sans-serif;
}

.hero {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0e1a 0%, #0d1f3c 50%, #0a1628 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    position: relative;
    overflow: hidden;
}

.hero::before {
    content: '';
    position: absolute;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(0, 120, 255, 0.08) 0%, transparent 70%);
    top: -100px;
    right: -100px;
    border-radius: 50%;
}

.hero::after {
    content: '';
    position: absolute;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(0, 200, 150, 0.06) 0%, transparent 70%);
    bottom: -50px;
    left: -50px;
    border-radius: 50%;
}

.grid-bg {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
    background-size: 60px 60px;
}

.logo-area {
    text-align: center;
    margin-bottom: 60px;
    position: relative;
    z-index: 1;
    animation: fadeDown 0.8s ease both;
}

.logo-icon {
    font-size: 56px;
    margin-bottom: 16px;
    display: block;
    filter: drop-shadow(0 0 20px rgba(0, 140, 255, 0.4));
}

.logo-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 48px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -1px;
    line-height: 1.1;
}

.logo-title span {
    background: linear-gradient(90deg, #0078ff, #00d4aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.logo-sub {
    margin-top: 12px;
    font-size: 16px;
    color: rgba(255,255,255,0.4);
    letter-spacing: 3px;
    text-transform: uppercase;
    font-weight: 300;
}

.cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    max-width: 720px;
    width: 100%;
    position: relative;
    z-index: 1;
}

.card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 36px 32px;
    cursor: pointer;
    transition: all 0.3s ease;
    text-decoration: none;
    display: flex;
    flex-direction: column;
    gap: 12px;
    animation: fadeUp 0.8s ease both;
    position: relative;
    overflow: hidden;
}

.card::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 20px;
    opacity: 0;
    transition: opacity 0.3s;
}

.card:hover {
    border-color: rgba(255,255,255,0.2);
    transform: translateY(-4px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.4);
}

.card.blue::before  { background: radial-gradient(circle at top left, rgba(0,120,255,0.12), transparent 60%); }
.card.green::before { background: radial-gradient(circle at top left, rgba(0,212,170,0.12), transparent 60%); }
.card.purple::before{ background: radial-gradient(circle at top left, rgba(130,80,255,0.12), transparent 60%); }
.card.orange::before{ background: radial-gradient(circle at top left, rgba(255,140,0,0.12), transparent 60%); }

.card:hover::before { opacity: 1; }

.card-icon {
    font-size: 32px;
    line-height: 1;
}

.card-title {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    font-family: 'Noto Sans KR', sans-serif;
}

.card-desc {
    font-size: 13px;
    color: rgba(255,255,255,0.4);
    line-height: 1.6;
    font-weight: 300;
}

.card-arrow {
    margin-top: auto;
    font-size: 18px;
    color: rgba(255,255,255,0.2);
    transition: all 0.3s;
    align-self: flex-end;
}

.card:hover .card-arrow { color: rgba(255,255,255,0.6); transform: translate(4px, -4px); }

.card.coming {
    opacity: 0.5;
    cursor: not-allowed;
}
.card.coming:hover { transform: none; box-shadow: none; }

.card:nth-child(1) { animation-delay: 0.1s; }
.card:nth-child(2) { animation-delay: 0.2s; }
.card:nth-child(3) { animation-delay: 0.3s; }
.card:nth-child(4) { animation-delay: 0.4s; }

.badge {
    display: inline-block;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 20px;
    background: rgba(255,140,0,0.2);
    color: rgba(255,180,0,0.8);
    border: 1px solid rgba(255,140,0,0.3);
    font-weight: 500;
    letter-spacing: 1px;
    align-self: flex-start;
}

@keyframes fadeDown {
    from { opacity: 0; transform: translateY(-20px); }
    to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}

.divider {
    width: 40px;
    height: 2px;
    background: linear-gradient(90deg, #0078ff, #00d4aa);
    margin: 0 auto 40px;
    border-radius: 2px;
    animation: fadeDown 0.8s 0.3s ease both;
    opacity: 0;
    animation-fill-mode: both;
}
</style>

<div class="hero">
    <div class="grid-bg"></div>

    <div class="logo-area">
        <span class="logo-icon">📈</span>
        <div class="logo-title">주식 <span>재무분석</span></div>
        <div class="logo-sub">Financial Intelligence Platform</div>
    </div>

    <div class="divider"></div>

    <div class="cards">
        <a class="card blue" href="/종목_상세" target="_self">
            <div class="card-icon">🔍</div>
            <div class="card-title">종목 상세</div>
            <div class="card-desc">개별 종목의 분기별 재무 데이터와 주가 추이를 한눈에 확인</div>
            <div class="card-arrow">↗</div>
        </a>

        <a class="card green" href="/전체_랭킹" target="_self">
            <div class="card-icon">📊</div>
            <div class="card-title">전체 랭킹</div>
            <div class="card-desc">ROE, 영익률 등 항목별로 전체 종목을 정렬하여 비교</div>
            <div class="card-arrow">↗</div>
        </a>

        <div class="card purple coming">
            <div class="card-icon">🌱</div>
            <div class="card-title">Grow</div>
            <div class="badge">COMING SOON</div>
            <div class="card-desc">성장성 분석 및 투자 인사이트 — 준비 중입니다</div>
            <div class="card-arrow">↗</div>
        </div>

        <a class="card orange" href="/설정" target="_self">
            <div class="card-icon">⚙️</div>
            <div class="card-title">설정</div>
            <div class="card-desc">DART API 키 설정 및 데이터 수집 관리</div>
            <div class="card-arrow">↗</div>
        </a>
    </div>
</div>
""", unsafe_allow_html=True)
