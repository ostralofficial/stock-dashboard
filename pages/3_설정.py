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
    try:
        client = get_client()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            res = client.table("stocks").select("stock_code", count="exact").execute()
            st.metric("총 종목 수", f"{res.count:,}개")
        with col2:
            res = client.table("financials").select("id", count="exact").execute()
            st.metric("재무 데이터", f"{res.count:,}행")
        with col3:
            res = client.table("prices").select("stock_code", count="exact").execute()
            st.metric("주가 데이터", f"{res.count:,}행")
        with col4:
            res = client.table("manual_data").select("stock_code", count="exact").execute()
            st.metric("수동 입력", f"{res.count:,}행")
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")

# ── Tab 2: 종목 관리 ──────────────────────────────────────
with tab2:
    st.subheader("종목 관리")
    stocks_df = get_all_stocks()

    inner_tab1, inner_tab2 = st.tabs(["종목 목록", "종목 추가"])

    with inner_tab1:
        st.caption(f"총 {len(stocks_df)}개 종목")
        if not stocks_df.empty:
            st.dataframe(
                stocks_df[["name", "stock_code", "corp_code", "market"]],
                use_container_width=True,
                height=400,
            )
            del_name = st.selectbox("삭제할 종목", ["선택하세요"] + stocks_df["name"].tolist())
            if del_name != "선택하세요":
                if st.button(f"'{del_name}' 삭제", type="secondary"):
                    code = stocks_df[stocks_df["name"] == del_name]["stock_code"].values[0]
                    delete_stock(code)
                    st.success("삭제 완료")
                    st.rerun()

    with inner_tab2:
        st.caption("종목 개별 추가")
        with st.form("add_stock_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("종목명", placeholder="삼성전자")
                new_code = st.text_input("종목코드 (6자리)", placeholder="005930")
            with c2:
                new_corp = st.text_input("DART corp_code (8자리)", placeholder="00126380")
                new_market = st.selectbox("시장", ["KRX", "KOSDAQ"])
            if st.form_submit_button("추가", type="primary"):
                if new_name and new_code and new_corp:
                    ok, msg = add_stock(new_code, new_corp, new_name, new_market)
                    if ok:
                        st.success(f"'{new_name}' 추가 완료!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("모든 항목을 입력해주세요")

# ── Tab 3: 데이터 수집 ────────────────────────────────────
with tab3:
    st.subheader("DART 재무제표 수집")

    dart_key = st.text_input("DART API 키", type="password",
                              help="이 세션에서만 사용됩니다")

    stocks_df2 = get_all_stocks()

    if not stocks_df2.empty and dart_key:
        year_range = st.slider("수집 연도", 2014, 2025, (2023, 2025))
        years = list(range(year_range[0], year_range[1] + 1))

        n = len(stocks_df2)
        st.caption(f"전체 {n}개 종목 · 오래된 순서부터 자동 수집")

        if st.button("수집 시작", type="primary"):
            from dart_collector import collect_batch

            target_df = stocks_df2[["stock_code", "corp_code", "name"]].reset_index(drop=True)

            # 마지막 수집 시각 기준으로 정렬 (오래된 것 / 미수집 → 우선)
            client_tmp = get_client()
            res = client_tmp.table("financials").select(
                "stock_code, updated_at"
            ).in_("stock_code", target_df["stock_code"].tolist()).order(
                "updated_at", desc=True
            ).execute()

            recent = {}
            if res.data:
                for r in res.data:
                    if r["stock_code"] not in recent:
                        recent[r["stock_code"]] = r["updated_at"]

            target_df = target_df.iloc[
                sorted(range(len(target_df)),
                       key=lambda i: recent.get(target_df.iloc[i]["stock_code"], "0000-00-00"))
            ].reset_index(drop=True)

            progress = st.progress(0)
            status = st.empty()
            log_placeholder = st.empty()
            logs = []

            def on_progress(current, total, name):
                progress.progress((current + 1) / total)
                status.text(f"수집 중: {name} ({current+1}/{total})")

            results = collect_batch(dart_key, target_df, years, on_progress)
            total_saved = sum(r["saved"] for r in results)
            st.success(f"완료: {total_saved:,}개 항목 저장")
            st.rerun()

    st.divider()

    # ── 수집 기록 ─────────────────────────────────────────
    st.subheader("수집 기록")
    try:
        client_log = get_client()
        log_res = (client_log.table("financials")
                   .select("stock_code, item, value, source, updated_at")
                   .order("updated_at", desc=True)
                   .limit(500)
                   .execute())

        if log_res.data:
            log_df = pd.DataFrame(log_res.data)
            stocks_map = dict(zip(stocks_df2["stock_code"], stocks_df2["name"])) if not stocks_df2.empty else {}
            log_df["종목명"] = log_df["stock_code"].map(stocks_map).fillna(log_df["stock_code"])
            log_df["수집일시"] = pd.to_datetime(log_df["updated_at"])

            # 종목별 최근 수집일 + 수집항목수 + 수집내용(항목 목록)
            summary = (log_df.groupby("종목명")
                       .agg(
                           최근수집일=("수집일시", "max"),
                           수집항목수=("item", "count"),
                           수집내용=("item", lambda x: ", ".join(sorted(x.unique())))
                       )
                       .reset_index()
                       .sort_values("종목명"))

            summary["최근수집일"] = summary["최근수집일"].dt.strftime("%Y-%m-%d %H:%M")
            st.dataframe(summary, use_container_width=True, height=500)
        else:
            st.info("아직 수집 기록이 없습니다.")
    except Exception as e:
        st.error(f"기록 조회 오류: {e}")

# ── Tab 4: 수동 입력 ──────────────────────────────────────
with tab4:
    st.subheader("수동 입력 (해외매출 / 수주잔고 등)")
    stocks_df3 = get_all_stocks()
    if stocks_df3.empty:
        st.info("종목을 먼저 추가해주세요")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        sel_name = st.selectbox("종목", stocks_df3["name"].tolist(), key="manual_name")
    with col2:
        sel_year = st.selectbox("연도", list(range(2025, 2013, -1)), key="manual_year")

    sel_code = stocks_df3[stocks_df3["name"] == sel_name]["stock_code"].values[0]

    MANUAL_ITEMS = [
        "해외매출1q", "해외매출2q", "해외매출3q", "해외매출4q", "해외매출",
        "해외매출비중", "수주잔고1q", "수주잔고2q", "수주잔고3q", "수주잔고4q",
    ]

    # 기존 값 불러오기
    client2 = get_client()
    existing = client2.table("manual_data").select("item, value").eq(
        "stock_code", sel_code).eq("year", sel_year).execute()
    existing_dict = {r["item"]: r["value"] for r in (existing.data or [])}

    with st.form("manual_form"):
        cols = st.columns(3)
        input_vals = {}
        for i, item in enumerate(MANUAL_ITEMS):
            with cols[i % 3]:
                default = float(existing_dict.get(item, 0.0))
                input_vals[item] = st.number_input(item, value=default, step=1.0, format="%.1f")
        memo = st.text_input("메모", "")
        if st.form_submit_button("저장", type="primary"):
            for item, value in input_vals.items():
                if value != 0.0:
                    client2.table("manual_data").upsert({
                        "stock_code": sel_code,
                        "year": sel_year,
                        "item": item,
                        "value": value,
                        "memo": memo,
                    }, on_conflict="stock_code,year,item").execute()
            st.success("저장 완료!")
            st.rerun()
