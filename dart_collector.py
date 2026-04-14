import requests
import time
import pandas as pd

DART_API_URL = "https://opendart.fss.or.kr/api"

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
    results = {}
    debug_info = []

    for fs_div, mapping in [
        ("IS", INCOME_MAP),
        ("BS", BALANCE_MAP),
        ("CF", CASHFLOW_MAP),
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
            status = data.get("status", "???")
            message = data.get("message", "")
            debug_info.append(f"{fs_div}: status={status} ({message})")

            if status != "000":
                continue

            for row in data.get("list", []):
                acnt = row.get("account_nm", "").strip()
                our_name = mapping.get(acnt)
                if not our_name:
                    continue
                val_str = row.get("thstrm_amount", "").replace(",", "").strip()
                if not val_str or val_str == "-":
                    continue
                try:
                    results[our_name] = float(val_str)
                except ValueError:
                    pass
            time.sleep(0.3)
        except Exception as e:
            debug_info.append(f"{fs_div}: 예외 발생 - {e}")
            print(f"  오류 ({fs_div}): {e}")

    results["__debug__"] = debug_info
    return results


def collect_stock(api_key, stock_code, corp_code, years, client):
    """한 종목 수집 후 Supabase에 직접 저장"""
    saved = 0
    errors = []
    batch = []

    for year in years:
        try:
            raw = fetch_financial_statements(api_key, corp_code, year)
            debug = raw.pop("__debug__", [])
            items = raw

            if not items:
                for d in debug:
                    if "status" in d and "000" not in d:
                        errors.append(f"{year}: {d}")
                if not any(str(year) in e for e in errors):
                    errors.append(f"{year}: DART 데이터 없음 (corp_code={corp_code})")
                continue

            for item, value in items.items():
                batch.append({
                    "stock_code": stock_code,
                    "year": int(year),
                    "quarter": 0,
                    "item": item,
                    "value": float(value),
                    "source": "DART",
                })
        except Exception as e:
            errors.append(f"{year}: {str(e)}")

    if batch:
        try:
            res = client.table("financials").upsert(
                batch,
                on_conflict="stock_code,year,quarter,item"
            ).execute()
            if res.data is not None:
                saved = len(batch)
            else:
                errors.append("저장오류: upsert 응답 없음")
        except Exception as e:
            errors.append(f"저장오류: {str(e)}")

    return saved, errors


def collect_batch(api_key, stocks_df, years, progress_callback=None, log_callback=None):
    """
    log_callback(record): 종목 하나 완료 시 즉시 호출
      record = {"stock_code", "name", "collected_at", "item_count", "years", "errors"}
    """
    from db import get_client
    from datetime import datetime

    client = get_client()
    total = len(stocks_df)
    results = []

    for i, row in enumerate(stocks_df.itertuples()):
        if progress_callback:
            progress_callback(i, total, row.name)

        saved, errors = collect_stock(
            api_key, row.stock_code, row.corp_code, years, client
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        record = {
            "stock_code": row.stock_code,
            "name": row.name,
            "collected_at": now_str,
            "item_count": saved,
            "years": f"{years[0]}~{years[-1]}",
            "errors": errors,
        }

        # 종목 완료 즉시 DB에 기록 저장
        if saved > 0:
            try:
                client.table("collect_log").insert({
                    "stock_code": record["stock_code"],
                    "name": record["name"],
                    "collected_at": record["collected_at"],
                    "item_count": record["item_count"],
                    "years": record["years"],
                }).execute()
            except Exception as e:
                errors.append(f"기록저장오류: {str(e)}")

        # UI 콜백 (실시간 표시용)
        if log_callback:
            log_callback(record)

        results.append({
            "name": row.name,
            "stock_code": row.stock_code,
            "saved": saved,
            "errors": errors,
        })
        time.sleep(0.2)

    return results
