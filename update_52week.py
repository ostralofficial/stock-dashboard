"""
매일 15시에 GitHub Actions로 실행되는 52주 데이터 수집 스크립트
수집한 데이터를 Supabase의 week52 테이블에 저장
"""
import os
import sys
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from supabase import create_client

def get_client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)

def get_all_stocks(client):
    res = client.table("stocks").select("stock_code, name").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def collect_52week(client, stocks):
    end   = datetime.today()
    start = end - timedelta(weeks=52)
    end_str   = end.strftime("%Y-%m-%d")
    start_str = start.strftime("%Y-%m-%d")
    today_str = end.strftime("%Y-%m-%d")

    batch = []
    total = len(stocks)

    for i, (_, row) in enumerate(stocks.iterrows()):
        print(f"[{i+1}/{total}] {row['name']} ({row['stock_code']})", end=" ")
        try:
            df = fdr.DataReader(row["stock_code"], start_str, end_str)
            if df is None or df.empty or len(df) < 20:
                print("→ 데이터 없음")
                continue

            high_52    = float(df["High"].max())
            low_52     = float(df["Low"].min())
            close_now  = float(df["Close"].iloc[-1])
            close_1y   = float(df["Close"].iloc[0])

            ret_52        = (close_now - close_1y) / close_1y if close_1y != 0 else None
            pct_from_high = (close_now - high_52)  / high_52  if high_52  != 0 else None
            pct_from_low  = (close_now - low_52)   / low_52   if low_52   != 0 else None

            batch.append({
                "stock_code":    row["stock_code"],
                "name":          row["name"],
                "date":          today_str,
                "close":         close_now,
                "high_52":       high_52,
                "low_52":        low_52,
                "return_52":     round(ret_52, 6)        if ret_52        is not None else None,
                "pct_from_high": round(pct_from_high, 6) if pct_from_high is not None else None,
                "pct_from_low":  round(pct_from_low, 6)  if pct_from_low  is not None else None,
            })
            print(f"→ {close_now:,.0f}원 / 52주고 {high_52:,.0f} / 수익률 {ret_52*100:.1f}%")

        except Exception as e:
            print(f"→ 오류: {e}")

    # 배치 upsert
    if batch:
        for chunk_start in range(0, len(batch), 200):
            chunk = batch[chunk_start:chunk_start+200]
            client.table("week52").upsert(
                chunk,
                on_conflict="stock_code,date"
            ).execute()
        print(f"\n✅ {len(batch)}개 종목 저장 완료 ({today_str})")
    else:
        print("\n⚠️ 저장된 데이터 없음")

if __name__ == "__main__":
    client = get_client()
    stocks = get_all_stocks(client)
    if stocks.empty:
        print("종목 없음")
        sys.exit(1)
    print(f"총 {len(stocks)}개 종목 수집 시작")
    collect_52week(client, stocks)
