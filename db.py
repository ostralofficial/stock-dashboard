import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client
 
def _get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.environ.get(key, "")
 
def get_client() -> Client:
    url = _get_secret("SUPABASE_URL")
    key = _get_secret("SUPABASE_KEY")
    return create_client(url, key)
 
def init_db():
    pass
 
def get_all_stocks():
    client = get_client()
    res = client.table("stocks").select("*").order("name").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()
 
def add_stock(stock_code, corp_code, name, market="KRX",
              parent_stock_code=None, is_preferred=0):
    client = get_client()
    try:
        client.table("stocks").upsert({
            "stock_code": stock_code,
            "corp_code": corp_code,
            "name": name,
            "market": market,
            "parent_stock_code": parent_stock_code,
            "is_preferred": is_preferred,
        }).execute()
        return True, "추가 완료"
    except Exception as e:
        return False, str(e)
 
def delete_stock(stock_code):
    client = get_client()
    for table in ["financials", "prices", "manual_data", "stocks"]:
        client.table(table).delete().eq("stock_code", stock_code).execute()
 
def upsert_financial(stock_code, year, quarter, item, value, source="DART"):
    client = get_client()
    client.table("financials").upsert({
        "stock_code": stock_code,
        "year": year,
        "quarter": quarter,
        "item": item,
        "value": value,
        "source": source,
    }, on_conflict="stock_code,year,quarter,item").execute()
 
def upsert_manual(stock_code, year, item, value, memo=""):
    client = get_client()
    client.table("manual_data").upsert({
        "stock_code": stock_code,
        "year": year,
        "item": item,
        "value": value,
        "memo": memo,
    }, on_conflict="stock_code,year,item").execute()
 
def get_financials(stock_codes, items, years=None):
    client = get_client()
    query = (client.table("financials")
             .select("stock_code, year, quarter, item, value, source")
             .in_("stock_code", list(stock_codes))
             .in_("item", list(items)))
    if years:
        query = query.in_("year", [int(y) for y in years])
    res = query.execute()
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    stocks = get_all_stocks()[["stock_code", "name", "is_preferred"]]
    return df.merge(stocks, on="stock_code", how="left")
 
def get_latest_prices(stock_codes):
    client = get_client()
    res = (client.table("prices")
           .select("stock_code, date, close")
           .in_("stock_code", list(stock_codes))
           .order("date", desc=True)
           .execute())
    if not res.data:
        return pd.DataFrame()
    df = pd.DataFrame(res.data)
    df = df.drop_duplicates(subset="stock_code", keep="first")
    stocks = get_all_stocks()[["stock_code", "name", "is_preferred"]]
    return df.merge(stocks, on="stock_code", how="left")
 
def upsert_price(stock_code, date, close):
    client = get_client()
    client.table("prices").upsert({
        "stock_code": stock_code,
        "date": str(date),
        "close": close,
    }, on_conflict="stock_code,date").execute()
 
def load_stock_financials(stock_code):
    client = get_client()
    res = (client.table("financials")
           .select("year, quarter, item, value")
           .eq("stock_code", stock_code)
           .order("year")
           .execute())
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()
 
def get_conn():
    return get_client()
