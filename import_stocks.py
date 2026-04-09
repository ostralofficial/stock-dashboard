"""
기존 EPS-ACCUM.xlsx의 simple 시트와 매핑 시트를 읽어
DB에 606개 종목을 일괄 등록하는 스크립트

사용법:
    python import_stocks.py --file EPS-ACCUM.xlsx
"""
import argparse
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import init_db, add_stock, get_conn

def import_from_excel(filepath: str):
    init_db()
    path = Path(filepath)
    if not path.exists():
        print(f"파일 없음: {filepath}")
        return

    # simple 시트에서 종목명 + 종목코드 추출
    simple = pd.read_excel(path, sheet_name="simple", header=None)
    stocks_raw = simple.iloc[1:, [1, 4]].dropna(subset=[4])
    stocks_raw.columns = ["name", "stock_code_full"]
    stocks_raw["stock_code"] = (
        stocks_raw["stock_code_full"]
        .str.replace("KRX:", "")
        .str.replace("KOSDAQ:", "")
        .str.replace("KOSPI:", "")
        .str.strip()
    )
    stocks_raw["market"] = stocks_raw["stock_code_full"].apply(
        lambda x: "KOSDAQ" if "KOSDAQ" in str(x) else "KRX"
    )

    # 매핑 시트에서 corp_code 추출
    mapping = pd.read_excel(path, sheet_name="매핑", header=0)
    mapping.columns = [c.strip() for c in mapping.columns]
    mapping["stock_code"] = mapping["stock_code"].astype(str).str.zfill(6)
    mapping["corp_code"] = mapping["corp_code"].astype(str).str.zfill(8)
    code_map = dict(zip(mapping["stock_code"], mapping["corp_code"]))

    # 합치기
    stocks_raw["corp_code"] = stocks_raw["stock_code"].map(code_map).fillna("")

    ok, fail, no_corp = 0, 0, 0
    for _, row in stocks_raw.iterrows():
        if not row["corp_code"] or row["corp_code"] == "00000000":
            no_corp += 1
            print(f"  corp_code 없음: {row['name']} ({row['stock_code']})")
            continue
        success, msg = add_stock(
            row["stock_code"], row["corp_code"], row["name"], row["market"]
        )
        if success:
            ok += 1
        else:
            fail += 1
            print(f"  실패: {row['name']} - {msg}")

    print(f"\n완료: {ok}개 등록 / {fail}개 실패 / {no_corp}개 corp_code 없음")

    # 결과 확인
    conn = get_conn()
    total = pd.read_sql("SELECT COUNT(*) as n FROM stocks", conn)["n"].values[0]
    conn.close()
    print(f"DB 내 총 종목 수: {total}개")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="EPS-ACCUM.xlsx", help="엑셀 파일 경로")
    args = parser.parse_args()
    import_from_excel(args.file)
