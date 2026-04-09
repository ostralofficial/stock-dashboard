import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json

from db import (
    init_db, get_all_stocks, add_stock, delete_stock,
    get_financials, get_latest_prices, upsert_manual, get_conn
)
from dart_collector import collect_batch, fetch_price_fdr

# ── 초기화 ──────────────────────────────────────────────
init_db()
st.set_page_config(
    page_title="주식 재무 분석",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 설정 파일 ────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"
def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {"api_key": "", "default_years": list(range(2014, 2026))}

def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

cfg = load_config()

# ── 사이드바 ─────────────────────────────────────────────
with st.sidebar:
    st.title("📈 주식 재무 분석")
    page = st.radio(
        "메뉴",
        ["대시보드", "종목 관리", "데이터 수집", "수동 입력", "설정"],
        label_visibility="collapsed",
    )

# ════════════════════════════════════════════════════════
# 페이지 1: 대시보드
# ════════════════════════════════════════════════════════
if page == "대시보드":
    st.header("대시보드")

    stocks_df = get_all_stocks()
    if stocks_df.empty:
        st.info("종목을 먼저 추가해주세요 → '종목 관리' 메뉴")
        st.stop()

    # ── 필터 영역 ─────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        selected_names = st.multiselect(
            "종목 선택",
            options=stocks_df["name"].tolist(),
            default=stocks_df["name"].tolist()[:5],
        )
    with col2:
        all_items = [
            "매출액", "영업이익", "당기순이익", "매출원가", "판관비",
            "자산총계", "부채총계", "자본총계", "현금성자산",
            "매출채권", "재고자산", "CFO", "투자활동CF", "재무활동CF", "감가상각",
        ]
        selected_items = st.multiselect(
            "항목 선택",
            options=all_items,
            default=["매출액", "영업이익", "당기순이익"],
        )
    with col3:
        all_years = list(range(2014, 2026))
        selected_years = st.multiselect(
            "연도",
            options=all_years,
            default=all_years[-5:],
        )

    if not selected_names or not selected_items:
        st.warning("종목과 항목을 선택해주세요")
        st.stop()

    selected_codes = stocks_df[stocks_df["name"].isin(selected_names)]["stock_code"].tolist()

    df = get_financials(selected_codes, selected_items, selected_years)

    if df.empty:
        st.warning("해당 조건의 데이터가 없습니다. '데이터 수집' 메뉴에서 수집해주세요.")
        st.stop()

    # ── 요약 카드 ─────────────────────────────────────────
    latest_year = df["year"].max()
    latest = df[df["year"] == latest_year]

    st.subheader(f"{latest_year}년 주요 지표")
    metric_cols = st.columns(min(len(selected_names), 4))
    for i, name in enumerate(selected_names[:4]):
        with metric_cols[i]:
            st.markdown(f"**{name}**")
            for item in selected_items[:3]:
                row = latest[(latest["name"] == name) & (latest["item"] == item)]
                if not row.empty:
                    val = row["value"].values[0]
                    st.metric(item, f"{val/1e8:.1f}억" if abs(val) >= 1e8 else f"{val:,.0f}")

    st.divider()

    # ── 그래프 영역 ───────────────────────────────────────
    chart_type = st.radio("그래프 유형", ["라인", "바", "멀티 종목 비교"], horizontal=True)

    if chart_type in ["라인", "바"]:
        for item in selected_items:
            item_df = df[(df["item"] == item) & (df["quarter"] == 0)]
            if item_df.empty:
                continue

            fig = go.Figure()
            for name in selected_names:
                sub = item_df[item_df["name"] == name].sort_values("year")
                if sub.empty:
                    continue
                y_vals = sub["value"] / 1e8  # 억원 단위

                if chart_type == "라인":
                    fig.add_trace(go.Scatter(
                        x=sub["year"], y=y_vals,
                        mode="lines+markers", name=name,
                        line=dict(width=2),
                    ))
                else:
                    fig.add_trace(go.Bar(
                        x=sub["year"], y=y_vals, name=name,
                    ))

            fig.update_layout(
                title=f"{item} 추이 (억원)",
                xaxis_title="연도",
                yaxis_title="억원",
                hovermode="x unified",
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

    else:  # 멀티 종목 비교
        year_compare = st.select_slider("비교 연도", options=selected_years, value=selected_years[-1])
        compare_df = df[(df["year"] == year_compare) & (df["quarter"] == 0)]

        for item in selected_items:
            item_df = compare_df[compare_df["item"] == item]
            if item_df.empty:
                continue
            fig = px.bar(
                item_df,
                x="name", y=item_df["value"] / 1e8,
                title=f"{year_compare}년 {item} 비교 (억원)",
                labels={"y": "억원", "name": "종목"},
                color="name",
            )
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ── 데이터 테이블 ─────────────────────────────────────
    with st.expander("원본 데이터 보기"):
        pivot = df[df["quarter"] == 0].pivot_table(
            index=["name", "year"], columns="item", values="value", aggfunc="first"
        ).reset_index()
        st.dataframe(pivot, use_container_width=True, height=300)
        st.download_button(
            "CSV 다운로드",
            data=pivot.to_csv(index=False, encoding="utf-8-sig"),
            file_name="financial_data.csv",
            mime="text/csv",
        )

# ════════════════════════════════════════════════════════
# 페이지 2: 종목 관리
# ════════════════════════════════════════════════════════
elif page == "종목 관리":
    st.header("종목 관리")

    stocks_df = get_all_stocks()

    tab1, tab2, tab3 = st.tabs(["종목 목록", "종목 추가", "엑셀 일괄 추가"])

    with tab1:
        st.caption(f"총 {len(stocks_df)}개 종목")
        if not stocks_df.empty:
            st.dataframe(
                stocks_df[["name", "stock_code", "corp_code", "market", "added_at"]],
                use_container_width=True,
                height=400,
            )
            del_name = st.selectbox("삭제할 종목", ["선택하세요"] + stocks_df["name"].tolist())
            if del_name != "선택하세요":
                if st.button(f"'{del_name}' 삭제", type="secondary"):
                    code = stocks_df[stocks_df["name"] == del_name]["stock_code"].values[0]
                    delete_stock(code)
                    st.success("삭제되었습니다")
                    st.rerun()

    with tab2:
        st.caption("종목 개별 추가")
        with st.form("add_stock_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("종목명", placeholder="삼성전자")
                new_code = st.text_input("종목코드 (6자리)", placeholder="005930")
            with c2:
                new_corp = st.text_input("DART corp_code (8자리)", placeholder="00126380")
                new_market = st.selectbox("시장", ["KRX", "KOSDAQ", "KOSPI"])
            submitted = st.form_submit_button("추가", type="primary")
            if submitted:
                if new_name and new_code and new_corp:
                    ok, msg = add_stock(new_code, new_corp, new_name, new_market)
                    if ok:
                        st.success(f"'{new_name}' 추가 완료!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("모든 항목을 입력해주세요")

    with tab3:
        st.caption("매핑 시트 엑셀 업로드로 일괄 추가")
        st.markdown("""
        엑셀 파일 형식:
        | corp_name | stock_code | corp_code |
        |-----------|------------|-----------|
        | 삼성전자  | 005930     | 00126380  |
        """)
        uploaded = st.file_uploader("엑셀 파일 (.xlsx)", type=["xlsx"])
        if uploaded:
            try:
                up_df = pd.read_excel(uploaded)
                up_df.columns = [c.strip() for c in up_df.columns]
                st.dataframe(up_df.head(10), use_container_width=True)
                st.caption(f"총 {len(up_df)}행 감지")
                if st.button("일괄 추가 실행", type="primary"):
                    ok_cnt, fail_cnt = 0, 0
                    for _, row in up_df.iterrows():
                        try:
                            code = str(row.get("stock_code", "")).zfill(6)
                            corp = str(row.get("corp_code", "")).zfill(8)
                            name = str(row.get("corp_name", ""))
                            if code and corp and name:
                                add_stock(code, corp, name)
                                ok_cnt += 1
                        except:
                            fail_cnt += 1
                    st.success(f"완료: {ok_cnt}개 추가, {fail_cnt}개 실패")
                    st.rerun()
            except Exception as e:
                st.error(f"파일 읽기 오류: {e}")

# ════════════════════════════════════════════════════════
# 페이지 3: 데이터 수집
# ════════════════════════════════════════════════════════
elif page == "데이터 수집":
    st.header("데이터 수집")

    api_key = cfg.get("api_key", "")
    if not api_key:
        st.warning("설정 메뉴에서 DART API 키를 먼저 입력해주세요")
        st.stop()

    stocks_df = get_all_stocks()
    if stocks_df.empty:
        st.info("종목을 먼저 추가해주세요")
        st.stop()

    tab1, tab2 = st.tabs(["재무제표 수집", "주가 수집"])

    with tab1:
        st.subheader("DART 재무제표 수집")

        col1, col2 = st.columns(2)
        with col1:
            target_names = st.multiselect(
                "수집할 종목",
                stocks_df["name"].tolist(),
                default=stocks_df["name"].tolist(),
                help="비워두면 전체 종목 수집"
            )
        with col2:
            year_range = st.slider("수집 연도 범위", 2014, 2025, (2020, 2025))
            years = list(range(year_range[0], year_range[1] + 1))

        # 예상 호출 수
        n_stocks = len(target_names) if target_names else len(stocks_df)
        estimated = n_stocks * len(years) * 3
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("수집 대상 종목", f"{n_stocks}개")
        col_b.metric("수집 연도", f"{len(years)}년")
        col_c.metric("예상 API 호출 수", f"{estimated:,}회")

        if estimated > 10000:
            days = -(-estimated // 10000)
            st.warning(f"하루 10,000회 제한으로 약 {days}일 소요. 종목 또는 연도 범위를 줄이거나 나눠서 수집하세요.")

        if st.button("수집 시작", type="primary"):
            target_df = stocks_df[stocks_df["name"].isin(target_names)] if target_names else stocks_df
            target_df = target_df[["stock_code", "corp_code", "name"]].reset_index(drop=True)

            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            logs = []

            def on_progress(current, total, name):
                progress_bar.progress(current / total)
                status_text.text(f"수집 중: {name} ({current+1}/{total})")

            results = collect_batch(api_key, target_df, years, on_progress)

            progress_bar.progress(1.0)
            total_saved = sum(r["saved"] for r in results)
            errors = [(r["name"], r["errors"]) for r in results if r["errors"]]

            st.success(f"수집 완료: 총 {total_saved:,}개 항목 저장")
            if errors:
                with st.expander(f"오류 {len(errors)}건"):
                    for name, errs in errors:
                        st.write(f"**{name}**: {', '.join(errs)}")

    with tab2:
        st.subheader("주가 수집 (FinanceDataReader)")
        price_names = st.multiselect("종목 선택", stocks_df["name"].tolist(), default=stocks_df["name"].tolist()[:10])
        price_start = st.date_input("시작일", value=pd.Timestamp("2014-01-01"))

        if st.button("주가 수집 시작"):
            price_codes = stocks_df[stocks_df["name"].isin(price_names)]["stock_code"].tolist()
            with st.spinner("주가 수집 중..."):
                fetch_price_fdr(price_codes, start=str(price_start))
            st.success("주가 수집 완료")

# ════════════════════════════════════════════════════════
# 페이지 4: 수동 입력
# ════════════════════════════════════════════════════════
elif page == "수동 입력":
    st.header("수동 입력 (해외매출 / 수주잔고 등)")

    stocks_df = get_all_stocks()
    if stocks_df.empty:
        st.info("종목을 먼저 추가해주세요")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        sel_name = st.selectbox("종목", stocks_df["name"].tolist())
    with col2:
        sel_year = st.selectbox("연도", list(range(2025, 2013, -1)))

    sel_code = stocks_df[stocks_df["name"] == sel_name]["stock_code"].values[0]

    MANUAL_ITEMS = [
        "해외매출1q", "해외매출2q", "해외매출3q", "해외매출4q", "해외매출",
        "해외매출비중", "수주잔고1q", "수주잔고2q", "수주잔고3q", "수주잔고4q",
        "기타항목1", "기타항목2",
    ]

    # 기존 값 불러오기
    conn = get_conn()
    existing = pd.read_sql(
        "SELECT item, value, memo FROM manual_data WHERE stock_code=? AND year=?",
        conn, params=(sel_code, sel_year)
    )
    conn.close()
    existing_dict = dict(zip(existing["item"], existing["value"]))

    # DART 공시 링크
    corp_code = stocks_df[stocks_df["name"] == sel_name]["corp_code"].values[0]
    dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
    st.markdown(f"[DART 공시 바로가기 →](https://dart.fss.or.kr/corp/searchCorpInfo.do?textCrpCond=Y&textCrpNm={sel_name})", unsafe_allow_html=False)

    st.divider()

    with st.form("manual_input_form"):
        st.caption(f"{sel_name} / {sel_year}년 수동 입력")
        input_vals = {}
        cols = st.columns(3)
        for i, item in enumerate(MANUAL_ITEMS):
            with cols[i % 3]:
                default = existing_dict.get(item, None)
                input_vals[item] = st.number_input(
                    item,
                    value=float(default) if default is not None else 0.0,
                    step=1.0,
                    format="%.1f",
                )
        memo = st.text_input("메모", "")
        if st.form_submit_button("저장", type="primary"):
            for item, value in input_vals.items():
                if value != 0.0:
                    upsert_manual(sel_code, sel_year, item, value, memo)
            st.success("저장 완료!")
            st.rerun()

    # 저장된 데이터 미리보기
    conn = get_conn()
    all_manual = pd.read_sql(
        "SELECT year, item, value, memo, updated_at FROM manual_data WHERE stock_code=? ORDER BY year DESC, item",
        conn, params=(sel_code,)
    )
    conn.close()
    if not all_manual.empty:
        with st.expander(f"{sel_name} 수동 입력 전체 내역"):
            st.dataframe(all_manual, use_container_width=True)

# ════════════════════════════════════════════════════════
# 페이지 5: 설정
# ════════════════════════════════════════════════════════
elif page == "설정":
    st.header("설정")

    with st.form("settings_form"):
        api_key = st.text_input(
            "DART API 키",
            value=cfg.get("api_key", ""),
            type="password",
            help="https://opendart.fss.or.kr 에서 발급"
        )
        st.caption("API 키는 로컬 config.json에만 저장되며 외부로 전송되지 않습니다")

        if st.form_submit_button("저장", type="primary"):
            cfg["api_key"] = api_key
            save_config(cfg)
            st.success("설정 저장 완료")

    st.divider()
    st.subheader("DB 정보")
    conn = get_conn()
    for table in ["stocks", "financials", "prices", "manual_data"]:
        count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn)["n"].values[0]
        st.metric(table, f"{count:,}행")
    conn.close()
