import streamlit as st

st.set_page_config(
    page_title="Ostral",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;700&display=swap');

[data-testid="stAppViewContainer"] {
    background-image: url("https://raw.githubusercontent.com/ostralofficial/stock-dashboard/main/Screenshot_20240304_054553_Naver%20Blog.jpg");
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    min-height: 100vh;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background: rgba(5, 10, 20, 0.65);
    z-index: 0;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stVerticalBlock"] { position: relative; z-index: 1; }
#MainMenu, footer { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stMainBlockContainer"] { padding: 0 !important; }

.layout {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 100vh;
    padding: 0 8vw;
    font-family: 'Space Grotesk', sans-serif;
}

.left h1 {
    font-size: 72px;
    font-weight: 700;
    color: #fff;
    letter-spacing: -3px;
    margin: 0;
    line-height: 1;
    background: linear-gradient(90deg, #ffffff, #7ec8e3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}



.right {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-end;
}

a.menu-item, a.menu-item:visited, a.menu-item:link {
    color: rgba(255,255,255,0.45) !important;
    text-decoration: none !important;
}
a.menu-item:hover {
    color: #ffffff !important;
    text-decoration: none !important;
}

.menu-item {
    font-size: 28px;
    font-weight: 500;
    color: rgba(255,255,255,0.45);
    text-decoration: none;
    letter-spacing: -0.5px;
    padding: 6px 0;
    position: relative;
    transition: color 0.25s;
    cursor: pointer;
    font-family: 'Space Grotesk', sans-serif;
    background: none;
    border: none;
    display: inline-block;
}

.menu-item::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 1px;
    background: rgba(255,255,255,0.6);
    transition: width 0.3s ease;
}

.menu-item:hover {
    color: #ffffff;
}

.menu-item:hover::after {
    width: 100%;
}

.menu-item.disabled {
    color: rgba(255,255,255,0.25);
    cursor: default;
    font-size: 22px;
}

.menu-item.disabled:hover { color: rgba(255,255,255,0.25); }
.menu-item.disabled::after { display: none; }

.coming-tag {
    font-size: 10px;
    color: rgba(255,200,80,0.6);
    letter-spacing: 2px;
    margin-left: 10px;
    font-weight: 300;
}
</style>

<div class="layout">
    <div class="left">
        <h1>Ostral</h1>
        </div>
    <div class="right">
        <a class="menu-item" href="/종목_상세" target="_self">Detail</a>
        <a class="menu-item" href="/전체_랭킹" target="_self">Screening</a>
        <span class="menu-item disabled">Grow <span class="coming-tag">SOON</span></span>
        <a class="menu-item" href="/설정" target="_self">Setting</a>
    </div>
</div>
""", unsafe_allow_html=True)
