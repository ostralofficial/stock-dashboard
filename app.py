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
    gap: 4px;
    align-items: flex-end;
}

/* 메뉴 버튼 스타일 */
div[data-testid="stButton"] > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 28px !important;
    font-weight: 500 !important;
    color: rgba(255,255,255,0.45) !important;
    padding: 6px 0 !important;
    border-radius: 0 !important;
    border-bottom: 1.5px solid transparent !important;
    transition: all 0.25s !important;
    text-align: right !important;
    width: auto !important;
    letter-spacing: -0.5px !important;
}
div[data-testid="stButton"] > button:hover {
    color: #ffffff !important;
    border-bottom: 1.5px solid rgba(255,255,255,0.5) !important;
    background: transparent !important;
}
div[data-testid="stButton"] > button:disabled {
    color: rgba(255,255,255,0.2) !important;
    font-size: 22px !important;
    cursor: default !important;
}
</style>
""", unsafe_allow_html=True)

# ── 레이아웃 ─────────────────────────────────────────────
col_left, col_right = st.columns([3, 1])

with col_left:
    st.markdown("""
    <div style="display:flex; align-items:center; min-height:100vh; padding-left:2vw;">
        <h1 style="font-family:'Space Grotesk',sans-serif; font-size:72px; font-weight:700;
                   letter-spacing:-3px; margin:0; background:linear-gradient(90deg,#fff,#7ec8e3);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Ostral</h1>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown("<div style='min-height:30vh'></div>", unsafe_allow_html=True)

    if st.button("Detail", key="btn_detail", use_container_width=False):
        st.switch_page("pages/1_종목_상세.py")

    if st.button("Screening", key="btn_screening", use_container_width=False):
        st.switch_page("pages/2_전체_랭킹.py")

    st.button("Grow  soon", key="btn_grow", disabled=True, use_container_width=False)

    if st.button("Setting", key="btn_setting", use_container_width=False):
        st.switch_page("pages/3_설정.py")
