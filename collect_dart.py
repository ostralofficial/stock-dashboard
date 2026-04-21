"""
GitHub Actions로 실행되는 DART 재무제표 수집 스크립트
환경변수: SUPABASE_URL, SUPABASE_KEY, DART_API_KEY
"""
import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime
from supabase import create_client

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
    "법인세비용": "법인세",
    "법인세비용(수익)": "법인세",
    "기본주당순이익(손실)": "EPS",
    "기본주당이익(손실)": "EPS",
    "주당배당금": "DPS",
}

BALANCE_MAP = {
    "자산총계": "자산총계",
    "부채총계": "부채총계",
    "자본총계": "자본총계",
    "유동자산": "유동자산",
    "유동부채": "유동부채",
    "비유동자산": "비유동자산",
    "유형자산": "유형자산",
    "현금및현금성자산": "현금성자산",
    "매출채권": "매출채권",
    "매출채권 및 기타채권": "매출채권",
    "재고자산": "재고자산",
    "단기차입금": "단기차입금",
    "매입채무": "매입채무",
    "매입채무 및 기타채무": "매입채무",
    "법인세부채": "법인세부채",
    "당기법인세부채": "법인세부채",
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

def get_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

def get_all_stocks(client):
    res = client.table("stocks").select("stock_code, corp_code, name").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def get_collected_codes(client, codes):
    """이미 DART 수집된 종목 조회"""
    collected = set()
    for i in range(0, len(codes), 200):
        chunk = codes[i:i+200]
        res = (client.table("financials")
               .select("stock_code")
               .in_("stock_code", chunk)
               .eq("source", "DART")
               .limit(1000)
               .execute())
        if res.data:
            for r in res.data:
                collected.add(r["stock_code"])
    return collected

def fetch_statements(api_key, corp_code, year, report_code="11011"):
    results = {}
    for fs_div, mapping in [("IS", INCOME_MAP), ("BS", BALANCE_MAP), ("CF", CASHFLOW_MAP)]:
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
                timeout=20,
            )
            data = resp.json()
            if data.get("status") != "000":
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
            print(f"  [{fs_div}] 오류: {e}")
    return results

def save_log(client, stock_code, name, item_count, years_str):
    try:
        client.table("collect_log").insert({
            "stock_code": stock_code,
            "name": name,
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item_count": item_count,
            "years": years_str,
        }).execute()
    except Exception:
        pass

def run(api_key, years, daily_limit=9000):
    client = get_client()
    stocks = get_all_stocks(client)
    if stocks.empty:
        print("종목 없음")
        sys.exit(1)

    all_codes = stocks["stock_code"].tolist()
    collected = get_collected_codes(client, all_codes)

    # 미수집 우선 정렬
    not_done = stocks[~stocks["stock_code"].isin(collected)]
    done     = stocks[stocks["stock_code"].isin(collected)]
    target   = pd.concat([not_done, done], ignore_index=True)

    years_str = f"{years[0]}~{years[-1]}"
    api_calls = 0
    calls_per_stock = len(years) * 3  # IS + BS + CF

    total = len(target)
    saved_total = 0
    print(f"총 {total}개 종목 | 미수집 {len(not_done)}개 | 연도: {years_str}")
    print(f"오늘 최대 수집 가능: {daily_limit // calls_per_stock}개 종목\n")

    for i, row in target.iterrows():
        # 하루 API 호출 한도 체크
        if api_calls + calls_per_stock > daily_limit:
            print(f"\n⚠️ 일일 한도 {daily_limit}회 도달 — 오늘은 여기까지")
            break

        print(f"[{i+1}/{total}] {row['name']} ({row['stock_code']})", end=" ")

        batch = []
        for year in years:
            items = fetch_statements(api_key, row["corp_code"], year)
            api_calls += 3
            if not items:
                continue
            for item, value in items.items():
                batch.append({
                    "stock_code": row["stock_code"],
                    "year": int(year),
                    "quarter": 0,
                    "item": item,
                    "value": float(value),
                    "source": "DART",
                })

        if batch:
            try:
                client.table("financials").upsert(
                    batch, on_conflict="stock_code,year,quarter,item"
                ).execute()
                saved_total += len(batch)
                save_log(client, row["stock_code"], row["name"], len(batch), years_str)
                print(f"→ {len(batch)}개 저장")
            except Exception as e:
                print(f"→ 저장오류: {e}")
        else:
            print("→ 데이터 없음")

        time.sleep(0.2)

    print(f"\n✅ 완료: {saved_total:,}개 항목 저장 | API 호출: {api_calls}회")

if __name__ == "__main__":
    api_key = os.environ.get("DART_API_KEY", "")
    if not api_key:
        print("❌ DART_API_KEY 환경변수 없음")
        sys.exit(1)

    # 수집 연도 설정 (최근 3년 + 올해)
    from datetime import datetime
    this_year = datetime.today().year
    years = list(range(this_year - 3, this_year + 1))

    run(api_key, years)
