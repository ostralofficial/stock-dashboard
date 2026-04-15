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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["DB 현황", "종목 관리", "데이터 수집", "수동 입력", "지표 계산"])

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
        st.caption(f"전체 {n}개 종목 · 미수집 종목 우선 자동 수집")

        # ── 단일 종목 테스트 ──────────────────────────────
        with st.expander("🔬 단일 종목 테스트 (문제 진단용)", expanded=False):
            test_name = st.selectbox("테스트할 종목", stocks_df2["name"].tolist(), key="test_stock")
            test_row = stocks_df2[stocks_df2["name"] == test_name].iloc[0]
            st.caption(f"stock_code: `{test_row['stock_code']}` | corp_code: `{test_row['corp_code']}`")
            test_year = st.selectbox("테스트 연도", list(range(2025, 2013, -1)), index=2, key="test_year")

            if st.button("테스트 수집", key="btn_test"):
                from dart_collector import fetch_financial_statements
                with st.spinner("DART API 호출 중..."):
                    try:
                        raw = fetch_financial_statements(dart_key, test_row["corp_code"], test_year)
                        debug_info = raw.pop("__debug__", [])

                        # DART 응답 상태 항상 표시
                        with st.expander("📡 DART 응답 상태 (디버그)", expanded=True):
                            for d in debug_info:
                                if "status=000" in d:
                                    st.success(d)
                                elif "status=" in d:
                                    st.error(d)
                                else:
                                    st.warning(d)

                        if raw:
                            st.success(f"✅ {len(raw)}개 항목 수신 성공!")
                            st.json(raw)
                            # DB 저장 테스트
                            try:
                                client_test = get_client()
                                batch = [{"stock_code": test_row["stock_code"], "year": int(test_year),
                                          "quarter": 0, "item": k, "value": float(v), "source": "DART"}
                                         for k, v in raw.items()]
                                res = client_test.table("financials").upsert(
                                    batch, on_conflict="stock_code,year,quarter,item"
                                ).execute()
                                if res.data is not None:
                                    st.success(f"✅ DB 저장 성공! ({len(batch)}행)")
                                else:
                                    st.error("❌ DB 저장 응답 없음")
                            except Exception as db_err:
                                st.error(f"❌ DB 저장 실패: {db_err}")
                        else:
                            st.warning("⚠️ DART 데이터 없음 — 위 응답 상태를 확인해주세요")
                            st.info("💡 2025년은 아직 공시 전일 수 있어요. 2023 또는 2024년으로 바꿔 보세요.")
                    except Exception as api_err:
                        st.error(f"❌ API 오류: {api_err}")

        if st.button("수집 시작", type="primary"):
            from dart_collector import collect_batch

            target_df = stocks_df2[["stock_code", "corp_code", "name"]].reset_index(drop=True)

            import random
            # DART로 실제 수집된 종목 조회 (source='DART')
            client_tmp = get_client()
            all_codes = target_df["stock_code"].tolist()

            dart_collected = set()
            for chunk_start in range(0, len(all_codes), 200):
                chunk = all_codes[chunk_start:chunk_start+200]
                res = client_tmp.table("financials").select(
                    "stock_code"
                ).in_("stock_code", chunk).eq("source", "DART").limit(1000).execute()
                if res.data:
                    for r in res.data:
                        dart_collected.add(r["stock_code"])

            # 미수집 / 수집완료 분리 후 각각 랜덤 섞기
            not_collected = target_df[~target_df["stock_code"].isin(dart_collected)].copy()
            collected = target_df[target_df["stock_code"].isin(dart_collected)].copy()

            not_collected = not_collected.sample(frac=1).reset_index(drop=True)
            collected = collected.sample(frac=1).reset_index(drop=True)

            target_df = pd.concat([not_collected, collected], ignore_index=True)

            first_name = target_df.iloc[0]["name"]
            st.info(f"미수집: {len(not_collected)}개 → 수집완료: {len(collected)}개 | 첫 번째: {first_name}")

            progress = st.progress(0)
            status_txt = st.empty()

            # 실시간 로그 테이블
            st.markdown("**실시간 수집 현황**")
            live_log_area = st.empty()
            live_logs = []  # {"종목명", "수집항목수", "수집일시", "상태"}

            def on_progress(current, total, name):
                progress.progress((current + 1) / total)
                status_txt.text(f"수집 중: {name} ({current+1}/{total})")

            def on_log(record):
                if record["item_count"] > 0:
                    live_logs.append({
                        "종목명": record["name"],
                        "수집항목": record["item_count"],
                        "수집일시": record["collected_at"],
                        "상태": "✅",
                    })
                else:
                    live_logs.append({
                        "종목명": record["name"],
                        "수집항목": 0,
                        "수집일시": record["collected_at"],
                        "상태": "⚠️ " + (record["errors"][0][:30] if record["errors"] else "데이터없음"),
                    })
                # 최근 20개만 표시 (최신이 위)
                display = list(reversed(live_logs[-20:]))
                live_log_area.dataframe(
                    pd.DataFrame(display),
                    use_container_width=True,
                    height=min(60 + len(display) * 35, 400),
                )

            results = collect_batch(dart_key, target_df, years, on_progress, on_log)
            total_saved = sum(r["saved"] for r in results)
            total_errors = [e for r in results for e in r.get("errors", [])]

            if total_saved > 0:
                st.success(f"✅ 완료: {total_saved:,}개 항목 저장 | {sum(1 for r in results if r['saved'] > 0)}개 종목 기록됨")
            else:
                st.error("⚠️ 저장된 항목이 없습니다. API 키 또는 corp_code를 확인해주세요.")

            if total_errors:
                with st.expander(f"⚠️ 오류 {len(total_errors)}건 보기"):
                    for e in total_errors[:50]:
                        st.text(e)

            st.rerun()

    st.divider()

    # ── 수집 기록 ─────────────────────────────────────────
    st.subheader("수집 기록")
    try:
        client_log = get_client()
        log_res = (client_log.table("collect_log")
                   .select("name, collected_at, item_count, years")
                   .order("collected_at", desc=True)
                   .limit(2000)
                   .execute())

        if log_res.data:
            log_df = pd.DataFrame(log_res.data)
            log_df.columns = ["종목명", "수집일시", "수집항목수", "수집연도"]

            # 종목별 최근 수집일 + 누적 수집 횟수
            summary = (log_df.groupby("종목명")
                       .agg(
                           최근수집일=("수집일시", "max"),
                           수집횟수=("수집일시", "count"),
                           수집연도=("수집연도", "last"),
                           총수집항목=("수집항목수", "sum"),
                       )
                       .reset_index()
                       .sort_values("종목명"))

            st.caption(f"총 {len(summary)}개 종목 수집 기록")
            st.dataframe(summary, use_container_width=True, height=500)
        else:
            st.info("아직 수집 기록이 없습니다. 수집 시작 후 여기에 기록이 쌓여요.")
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

# ── Tab 5: 지표 계산 ──────────────────────────────────────
with tab5:
    st.subheader("파생 지표 자동 계산")
    st.caption("DART 수집 데이터를 바탕으로 PER, PBR, ROE, ROIC, 적정가격 등을 계산해 DB에 저장합니다.")

    # ── BBB 채권 수익률 설정 ──────────────────────────────
    st.markdown("**BBB 5년채 수익률 설정**&nbsp;&nbsp;&nbsp;[채권수익률 확인 ↗ 한국신용평가](https://www.kisrating.com/ratingsStatistics/statics_spread.do)")

    # pykrx로 자동 조회
    auto_bbb = None
    try:
        from pykrx import bond
        from datetime import datetime, timedelta
        _end = datetime.today().strftime("%Y%m%d")
        _start = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
        _df = bond.get_otc_treasury_yields(_start, _end, "회사채BBB-")
        if _df is not None and not _df.empty:
            auto_bbb = float(_df["수익률"].iloc[-1])
    except Exception:
        pass

    col_bbb1, col_bbb2 = st.columns([2, 1])
    with col_bbb1:
        if auto_bbb:
            st.success(f"pykrx 자동 조회: **BBB- 3년 {auto_bbb:.2f}%** (KRX 기준)")
        else:
            st.warning("pykrx 자동 조회 실패 — 수동 입력값을 사용합니다")
    with col_bbb2:
        manual_bbb = st.number_input(
            "BBB채권수익률 직접 입력 (%)",
            min_value=0.0, max_value=30.0,
            value=auto_bbb if auto_bbb else 4.5,
            step=0.01, format="%.2f",
            help="KIS Rating(kisrating.com)에서 확인한 BBB 5년 수익률을 입력하세요. 입력 시 자동 조회값보다 우선 적용됩니다."
        )

    # 실제 사용할 BBB 수익률 결정
    use_bbb = manual_bbb if manual_bbb > 0 else (auto_bbb or 4.5)
    st.caption(f"적용될 BBB 수익률: **{use_bbb:.2f}%** ({use_bbb/100:.4f})")

    st.divider()

    # ── 계산 실행 ─────────────────────────────────────────
    st.markdown("**계산 실행**")

    calc_mode = st.radio(
        "계산 범위",
        ["전체 종목", "특정 종목만"],
        horizontal=True,
    )

    stocks_df5 = get_all_stocks()
    sel_calc_stock = None
    if calc_mode == "특정 종목만" and not stocks_df5.empty:
        sel_calc_stock = st.selectbox("종목 선택", stocks_df5["name"].tolist(), key="calc_stock")

    if st.button("계산 시작", type="primary", key="btn_calc"):
        from calculate_derived import calculate_derived, get_current_price
        import pandas as pd

        client_calc = get_client()

        if calc_mode == "특정 종목만" and sel_calc_stock:
            targets = stocks_df5[stocks_df5["name"] == sel_calc_stock]
        else:
            targets = stocks_df5

        progress_c = st.progress(0)
        status_c = st.empty()
        total_c = len(targets)
        saved_c = 0
        errors_c = []

        for idx, (_, row) in enumerate(targets.iterrows()):
            progress_c.progress((idx + 1) / total_c)
            status_c.text(f"계산 중: {row['name']} ({idx+1}/{total_c})")

            try:
                res = (client_calc.table("financials")
                       .select("year, quarter, item, value")
                       .eq("stock_code", row["stock_code"])
                       .execute())
                if not res.data:
                    continue

                fin_df = pd.DataFrame(res.data)
                price = get_current_price(row["stock_code"])

                records = calculate_derived(
                    row["stock_code"], fin_df,
                    price=price,
                    bbb_rate=use_bbb / 100,
                )
                if records:
                    client_calc.table("financials").upsert(
                        records,
                        on_conflict="stock_code,year,quarter,item"
                    ).execute()
                    saved_c += len(records)
            except Exception as e:
                errors_c.append(f"{row['name']}: {e}")

        status_c.empty()
        progress_c.progress(1.0)

        if saved_c > 0:
            st.success(f"✅ 완료! {saved_c:,}개 파생 지표 저장됨")
        else:
            st.warning("저장된 지표가 없습니다. 먼저 DART 수집을 완료해주세요.")

        if errors_c:
            with st.expander(f"⚠️ 오류 {len(errors_c)}건"):
                for e in errors_c[:30]:
                    st.text(e)

    # ── 계산 항목 안내 ────────────────────────────────────
    with st.expander("계산되는 항목 목록"):
        st.markdown("""
| 항목 | 공식 |
|------|------|
| 매출증가 / 영익증가 / 순익증가 | (올해 - 작년) / abs(작년) |
| 매출원가률 / 영익률 / 순익률 / 판관비률 | 각 항목 / 매출액 |
| 부채비율 | 부채총계 / 자본총계 |
| ROE | 순이익 / 자본총계 |
| ROIC | (영업이익 - 법인세) / (유동자산 - 유동부채 + 유형자산) |
| EBITDA | 영업이익 + 감가상각 |
| FCF | 영업활동CF - abs(투자활동CF) |
| BPS | 자본총계 / 주식수 |
| EPS | 순이익 / 주식수 |
| 배당총액 | DPS × 주식수 |
| 배당성향 | 배당총액 / 순이익 |
| 배당수익률 | DPS / 현재가 |
| 주식소각비율 | (전년주식수 - 올해주식수) / 전년주식수 |
| PER | 현재가 / EPS |
| PBR | 현재가 / BPS |
| 적정가격 | (BPS + (EPS₀×3 + EPS₋₁×2 + EPS₋₂) / 6 × 10) / 2 |
| RIM가격 | BPS + BPS × (ROE평균 - BBB%) / BBB% |
| 서준식교수 | BPS × (1+ROE평균)¹⁰ / 현재가 - (1+BBB%)¹⁰ |
| 10년가격 | BPS × (1+ROE평균)¹⁰ |
| 기대수익률 | (적정가격 / 현재가)^(1/10) - 1 |
        """)
