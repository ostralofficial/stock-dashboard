import requests
import time
import pandas as pd
from db import upsert_financial, get_conn

DART_API_URL = "https://opendart.fss.or.kr/api"

# DART 계정과목명 → 우리 항목명 매핑
INCOME_MAP = {
    "매출액": "매출액",
    "영업이익": "영업이익",
    "영업이익(손실)": "영업이익",
    "당기순이익": "당기순이익",
    "당기순이익(손실)": "당기순이익",
    "매출원가": "매출원가",
    "판매비와관리비": "판관비",
    "판매비와관리비합계": "판관비",
}

BALANCE_MAP = {
    "자산총계": "자산총계",
    "부채총계": "부채총계",
    "자본총계": "자본총계",
    "유동자산": "유동자산",
    "비유동자산": "비유동자산",
    "유동부채": "유동부채",
    "비유동부채": "비유동부채",
    "현금및현금성자산": "현금성자산",
    "매출채권": "매출채권",
    "재고자산": "재고자산",
    "단기차입금": "단기차입금",
    "매입채무": "매입채무",
}

CASHFLOW_MAP = {
    "영업활동으로인한현금흐름": "CFO",
    "영업활동 현금흐름": "CFO",
    "투자활동으로인한현금흐름": "투자활동CF",
    "투자활동 현금흐름": "투자활동CF",
    "재무활동으로인한현금흐름": "재무활동CF",
    "재무활동 현금흐름": "재무활동CF",
    "감가상각비": "감가상각",
}

def fetch_financial_statements(api_key, corp_code, year, report_code="11011"):
    """
    report_code:
      11011 = 사업보고서 (연간)
      11012 = 반기보고서
      11013 = 1분기
      11014 = 3분기
    """
    results = {}

    for fs_div, label, mapping in [
        ("IS", "손익계산서", INCOME_MAP),
        ("BS", "재무상태표", BALANCE_MAP),
        ("CF", "현금흐름표", CASHFLOW_MAP),
    ]:
        try:
            resp = requests.get(
                f"{DART_API_URL}/fnlttSinglAcntAll.json",
                params={
                    "crtfc_key": api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": report_code,
                    "fs_div": fs_div,
                },
                timeout=15,
            )
            data = resp.json()
            if data.get("status") != "000":
                continue

            for row in data.get("list", []):
                acnt = row.get("account_nm", "").strip()
                our_name = mapping.get(acnt)
                if not our_name:
                    continue
                val_str = row.get("thstrm_amount", "").replace(",", "").replace("-", "")
                if not val_str:
                    continue
                try:
                    results[our_name] = float(val_str)
                except ValueError:
                    pass

            time.sleep(0.3)  # API 속도 제한 준수

        except Exception as e:
            print(f"  오류 ({label}): {e}")

    return results

def collect_stock(api_key, stock_code, corp_code, years, callback=None):
    """한 종목의 여러 연도 데이터 수집"""
    saved = 0
    errors = []

    for year in years:
        try:
            items = fetch_financial_statements(api_key, corp_code, year)
            for item, value in items.items():
                upsert_financial(stock_code, year, 0, item, value, source="DART")
                saved += 1
            if callback:
                callback(f"{year}년 수집완료 ({len(items)}개 항목)")
        except Exception as e:
            errors.append(f"{year}: {str(e)}")

    return saved, errors

def collect_batch(api_key, stocks_df, years, progress_callback=None):
    """
    stocks_df: columns = [stock_code, corp_code, name]
    진행상황을 progress_callback(current, total, name)으로 리포트
    """
    total = len(stocks_df)
    results = []

    for i, row in enumerate(stocks_df.itertuples()):
        if progress_callback:
            progress_callback(i, total, row.name)

        saved, errors = collect_stock(
            api_key, row.stock_code, row.corp_code, years
        )
        results.append({
            "name": row.name,
            "stock_code": row.stock_code,
            "saved": saved,
            "errors": errors,
        })
        time.sleep(0.2)

    return results

def fetch_price_fdr(stock_codes, start="2014-01-01"):
    """FinanceDataReader로 주가 수집 (DART 한도 무관)"""
    try:
        import FinanceDataReader as fdr
        from db import upsert_price
        for code in stock_codes:
            try:
                df = fdr.DataReader(code, start)
                for date, row in df.iterrows():
                    upsert_price(code, date.strftime("%Y-%m-%d"), row["Close"])
                time.sleep(0.1)
            except Exception as e:
                print(f"  주가 오류 {code}: {e}")
    except ImportError:
        print("FinanceDataReader 미설치: pip install finance-datareader")
