import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from db import get_all_stocks, get_client, add_stock, delete_stock

st.set_page_config(
    page_title="Setting",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
.home-btn button {
    background: rgba(0,0,0,0.06) !important;
    border: 1px solid rgba(0,0,0,0.12) !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)

# 홈 버튼
with st.container():
    st.markdown('<div class="home-btn">', unsafe_allow_html=True)
    if st.button("← Home"):
        st.switch_page("app.py")
    st.markdown('</div>', unsafe_allow_html=True)

st.header("Setting")

tab1, tab2, tab3, tab4 = st.tabs(["DB 현황", "종목 관리", "데이터 수집", "수동 입력"])

# ── Tab 1: DB 현황 ────────────────────────────────────────
with tab1:
    st.subheader("DB 현황")
    try
