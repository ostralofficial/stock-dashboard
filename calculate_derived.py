"""
파생 지표 자동 계산 모듈
DART에서 수집한 원본 데이터 → 계산 지표 → DB 저장

계산 항목:
  매출증가, 영익증가, 순익증가, EPS증가
  매출원가률, 매출총이익률, 영익률, 순익률, 판관비률
  부채비율, ROE, ROIC
  EBITDA, FCF
  BPS, EPS(계산), 배당총액, 배당성향, 배당수익률
  PER, PBR
  적정가격, RIM가격, 서준식교수, 기대수익률
  주식소각비율
"""

import pandas as pd
import time

# BBB- 3년 채권 수익률 pykrx로 조회
def get_bbb_rate_from_pykrx():
    try:
        from pykrx import bond
        from datetime import datetime, timedelta
        end = datetime.today().strftime("%Y%m%d")
        start = (datetime.today() - timedelta(days=30)).strftime("%Y%m%d")
        df = bond.get_otc_treasury_yields(start, end, "회사채BBB-")
        if df is not None and not df.empty:
            return float(df["수익률"].iloc[-1]) / 100
    except Exception:
        pass
    return None

def get_bbb_rate(manual_rate=None):
    """BBB 수익률: 수동입력 우선, 없으면 pykrx, 둘 다 없으면 기본값 4.5%"""
    if manual_rate is not None and manual_rate > 0:
        return manual_rate / 100
    auto = get_bbb_rate_from_pykrx()
    if auto is not None:
        return auto
    return 0.045  # 기본값

def get_current_price(stock_code):
    """최신 주가 조회 - FinanceDataReader 우선, 실패시 None"""
    try:
        import FinanceDataReader as fdr
        from datetime import datetime, timedelta
        end = datetime.today().strftime("%Y-%m-%d")
        start = (datetime.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        df = fdr.DataReader(stock_code, start, end)
        if df is not None and not df.empty:
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None

def calculate_derived(stock_code, fin_df, price=None, bbb_rate=0.045):
    """
    fin_df: DB에서 가져온 해당 종목의 재무 데이터 (year, quarter, item, value)
    반환: [{stock_code, year, quarter, item, value, source}, ...]
    """
    results = []

    # 연간 데이터(quarter=0)만 피벗
    ann = fin_df[fin_df["quarter"] == 0].copy()
    if ann.empty:
        return results

    pivot = ann.pivot_table(index="year", columns="item", values="value", aggfunc="first")
    years = sorted(pivot.index.tolist())

    def v(year, item):
        """안전하게 값 가져오기"""
        try:
            val = pivot.loc[year, item]
            if pd.isna(val):
                return None
            return float(val)
        except Exception:
            return None

    def save(year, item, value):
        if value is None or pd.isna(value):
            return
        results.append({
            "stock_code": stock_code,
            "year": int(year),
            "quarter": 0,
            "item": item,
            "value": round(float(value), 6),
            "source": "CALC",
        })

    for yr in years:
        prev = yr - 1

        매출 = v(yr, "매출액")
        매출_prev = v(prev, "매출액")
        영업이익 = v(yr, "영업이익")
        영업이익_prev = v(prev, "영업이익")
        순이익 = v(yr, "당기순이익")
        순이익_prev = v(prev, "당기순이익")
        매출원가 = v(yr, "매출원가")
        판관비 = v(yr, "판관비")
        자산 = v(yr, "자산총계")
        부채 = v(yr, "부채총계")
        자본 = v(yr, "자본총계")
        유동자산 = v(yr, "유동자산")
        유동부채 = v(yr, "유동부채")
        유형자산 = v(yr, "유형자산")
        법인세 = v(yr, "법인세")
        cfo = v(yr, "CFO")
        투자cf = v(yr, "투자활동CF")
        감가 = v(yr, "감가상각")
        주식수 = v(yr, "주식수")
        주식수_prev = v(prev, "주식수")
        dps = v(yr, "DPS")
        eps_dart = v(yr, "EPS")
        bps_prev = v(prev, "BPS_CALC") or v(prev, "BPS")

        # ── 성장률 ──────────────────────────────────────────
        if 매출 and 매출_prev and 매출_prev != 0:
            save(yr, "매출증가", (매출 - 매출_prev) / abs(매출_prev))
        if 영업이익 and 영업이익_prev and 영업이익_prev != 0:
            save(yr, "영익증가", (영업이익 - 영업이익_prev) / abs(영업이익_prev))
        if 순이익 and 순이익_prev and 순이익_prev != 0:
            save(yr, "순익증가", (순이익 - 순이익_prev) / abs(순이익_prev))

        # ── 이익률 ──────────────────────────────────────────
        if 매출 and 매출 != 0:
            if 매출원가:
                save(yr, "매출원가률", 매출원가 / 매출)
                save(yr, "매출총이익률", (매출 - 매출원가) / 매출)
            if 영업이익:
                save(yr, "영익률", 영업이익 / 매출)
            if 순이익:
                save(yr, "순익률", 순이익 / 매출)
            if 판관비:
                save(yr, "판관비률", 판관비 / 매출)

        # ── 재무비율 ────────────────────────────────────────
        if 부채 and 자본 and 자본 != 0:
            save(yr, "부채비율", 부채 / 자본)
        if 순이익 and 자본 and 자본 != 0:
            save(yr, "ROE", 순이익 / 자본)

        # ── ROIC = (영업이익 - 법인세) / (유동자산 - 유동부채 + 유형자산) ──
        if 영업이익 and 유동자산 and 유동부채 and 유형자산:
            nopat = 영업이익 - (법인세 or 0)
            invested = (유동자산 - 유동부채) + 유형자산
            if invested != 0:
                save(yr, "ROIC", nopat / invested)

        # ── 현금흐름 ────────────────────────────────────────
        if 영업이익 and 감가:
            save(yr, "EBITDA", 영업이익 + 감가)
        if cfo and 투자cf:
            save(yr, "FCF", cfo - abs(투자cf))

        # ── 주당 지표 ───────────────────────────────────────
        if 자본 and 주식수 and 주식수 != 0:
            bps = 자본 / 주식수
            save(yr, "BPS_CALC", bps)
        else:
            bps = v(yr, "BPS")

        if 순이익 and 주식수 and 주식수 != 0:
            eps = 순이익 / 주식수
            save(yr, "EPS_CALC", eps)
        else:
            eps = eps_dart

        # ── 배당 ────────────────────────────────────────────
        if dps and 주식수:
            배당총액 = dps * 주식수
            save(yr, "배당총액", 배당총액)
            if price:
                save(yr, "배당수익률", dps / price)
            if eps and eps != 0:
                save(yr, "배당성향", (dps * 주식수) / abs(순이익 or eps))

        # ── 주식소각비율 ─────────────────────────────────────
        if 주식수 and 주식수_prev and 주식수_prev != 0:
            save(yr, "주식소각비율", (주식수_prev - 주식수) / 주식수_prev)

        # ── PER / PBR ────────────────────────────────────────
        if price:
            if eps and eps != 0:
                save(yr, "PER", price / abs(eps))
            if bps and bps != 0:
                save(yr, "PBR", price / bps)

    # ── 밸류에이션 (최신 연도 기준) ─────────────────────────
    if len(years) >= 1:
        yr = years[-1]
        prev1 = yr - 1
        prev2 = yr - 2

        bps_now = None
        try:
            bps_now = [r["value"] for r in results
                       if r["year"] == yr and r["item"] == "BPS_CALC"]
            bps_now = bps_now[0] if bps_now else v(yr, "BPS")
        except Exception:
            bps_now = v(yr, "BPS")

        eps_now = None
        try:
            eps_now = [r["value"] for r in results
                       if r["year"] == yr and r["item"] == "EPS_CALC"]
            eps_now = eps_now[0] if eps_now else v(yr, "EPS")
        except Exception:
            eps_now = v(yr, "EPS")

        eps_1 = v(prev1, "EPS") or v(prev1, "EPS_CALC")
        eps_2 = v(prev2, "EPS") or v(prev2, "EPS_CALC")

        # ROE 최근 3년 평균
        roe_list = [r["value"] for r in results
                    if r["item"] == "ROE" and r["year"] in [yr, prev1, prev2]]
        roe_avg = sum(roe_list) / len(roe_list) if roe_list else None
        if roe_avg:
            save(yr, "ROE평균", roe_avg)

        # 적정가격 = (올해BPS + (올해EPS*3 + 1년전EPS*2 + 2년전EPS) / 6 * 10) / 2
        if bps_now and eps_now and eps_1 and eps_2:
            eps_avg = (eps_now * 3 + eps_1 * 2 + eps_2) / 6
            적정가격 = (bps_now + eps_avg * 10) / 2
            save(yr, "적정가격", 적정가격)

        # RIM가격 = BPS + BPS * (ROE평균 - BBB수익률) / BBB수익률
        if bps_now and roe_avg:
            rim = bps_now + bps_now * (roe_avg - bbb_rate) / bbb_rate
            save(yr, "RIM가격", rim)

        # 서준식교수 = (BPS * (1 + ROE평균)^10) / 현재가 - (1+BBB수익률)^10
        if bps_now and roe_avg and price and price != 0:
            target_10y = bps_now * ((1 + roe_avg) ** 10)
            hurdle = (1 + bbb_rate) ** 10
            save(yr, "서준식교수", target_10y / price - hurdle)
            save(yr, "10년가격", target_10y)

        # 기대수익률 = (적정가격 / 현재가)^(1/10) - 1
        적정 = next((r["value"] for r in results
                     if r["year"] == yr and r["item"] == "적정가격"), None)
        if 적정 and price and price != 0:
            save(yr, "기대수익률", (적정 / price) ** (1/10) - 1)

    return results


def run_all(client, bbb_rate=0.045, progress_callback=None):
    """전체 종목 파생 지표 계산 후 DB 저장"""
    from db import get_all_stocks

    stocks = get_all_stocks()
    total = len(stocks)
    total_saved = 0

    for i, row in stocks.iterrows():
        if progress_callback:
            progress_callback(i, total, row["name"])

        # 재무 데이터 로드
        res = (client.table("financials")
               .select("year, quarter, item, value")
               .eq("stock_code", row["stock_code"])
               .execute())
        if not res.data:
            continue

        fin_df = pd.DataFrame(res.data)
        price = get_current_price(row["stock_code"])

        records = calculate_derived(row["stock_code"], fin_df, price, bbb_rate)
        if not records:
            continue

        try:
            client.table("financials").upsert(
                records,
                on_conflict="stock_code,year,quarter,item"
            ).execute()
            total_saved += len(records)
        except Exception as e:
            print(f"  저장오류 ({row['name']}): {e}")

        time.sleep(0.1)

    return total_saved
