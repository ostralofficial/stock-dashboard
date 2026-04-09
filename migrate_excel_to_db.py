"""
EPS-ACCUM.xlsx의 data 시트 전체를 stock_data.db로 이관하는 스크립트.

사용법:
    python migrate_excel_to_db.py --file EPS-ACCUM.xlsx

소요 시간: 약 2~5분 (606종목 × 12년)
"""
import argparse
import pandas as pd
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import init_db, get_conn

# ── 컬럼 인덱스 정의 ─────────────────────────────────────

# 연간 항목: {DB저장명: 엑셀컬럼인덱스}
ANNUAL_COLS = {
    "매출액":        61,
    "매출증가":      62,
    "매출원가":      67,
    "매출원가증":    68,
    "매출원가률":    73,
    "매출총이익":    78,
    "매출총이익률":  79,
    "판관비":        85,
    "판관비증":      86,
    "판관비률":      91,
    "영업이익":      96,
    "영익증":        97,
    "영익률":        102,
    "순이익":        107,
    "순익증":        108,
    "순익률":        109,
    "EPS":           114,
    "EPS증가률":     115,
    "5년eps대비":    116,
    "자산총계":      42,
    "자본총계":      55,
    "부채비율":      56,
    "CFO":           126,
    "주당CFO":       127,
    "투자활동CF":    136,
    "재무활동CF":    145,
    "FCF":           155,
    "주당FCF":       156,
    "감가상각":      157,
    "EBITDA":        158,
    "주식수":        159,
    "주식수변동":    160,
    "주식수변동3y":  161,
    "DPS":           163,
    "배당증가":      164,
    "5년dps대비":    165,
    "배당성향":      166,
    "배당총액":      167,
    "BPS":           169,
    "적정가격":      170,
    "상속세법적정가":171,
    "ROE":           172,
    "ROE평균":       173,
    "RIM가격":       175,
    "기대수익률":    176,
    "EPS10년":       177,
    "10년가격":      178,
    "해외매출":      11,
    "해외매출증":    12,
    "해외매출비중":  17,
}

# 분기 항목: {DB저장명: (q1인덱스, q2인덱스, q3인덱스, q4인덱스)}
QUARTER_COLS = {
    "매출":      (57,  58,  59,  60),
    "매출원가":  (63,  64,  65,  66),
    "매출총이익":(74,  75,  76,  77),
    "판관비":    (81,  82,  83,  84),
    "영업이익":  (92,  93,  94,  95),
    "순이익":    (103, 104, 105, 106),
    "EPS":       (110, 111, 112, 113),
    "현금성자산":(22,  23,  24,  25),
    "매출채권":  (26,  27,  28,  29),
    "재고자산":  (34,  35,  36,  37),
    "단기차입금":(43,  44,  45,  46),
    "부채":      (51,  52,  53,  54),
    "영업CF":    (118, 119, 120, 121),
    "FCF":       (151, 152, 153, 154),
    "해외매출":  (7,   8,   9,   10),
    "수주잔고":  (18,  19,  20,  21),
}


def safe_float(val):
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except:
        return None


def clean_code(code_str):
    return (str(code_str)
            .replace("KRX:", "").replace("Krx:", "").replace("krx:", "")
            .replace("KOSDAQ:", "").replace("Kosdaq:", "").replace("kosdaq:", "")
            .replace("KOSPI:", "").replace("KONEX:", "")
            .strip())


def migrate(filepath: str):
    init_db()
    path = Path(filepath)
    if not path.exists():
        print(f"파일 없음: {filepath}")
        return

    print("엑셀 로딩 중...")
    raw = pd.read_excel(str(path), sheet_name="data", header=None)

    # 종목 헤더 행 찾기 (컬럼2 == '사업')
    cond = raw.iloc[:, 2].astype(str) == "사업"
    header_rows = raw[cond].index.tolist()
    print(f"총 종목 블록: {len(header_rows)}개")

    conn = get_conn()
    total_rows = 0
    skipped = 0

    for idx, hr in enumerate(header_rows):
        stock_name = str(raw.iloc[hr, 1]).strip()
        code_raw   = str(raw.iloc[hr, 5]).strip()
        stock_code = clean_code(code_raw)

        # DB에 등록된 종목인지 확인
        db_row = conn.execute(
            "SELECT stock_code FROM stocks WHERE stock_code=? OR name=?",
            (stock_code, stock_name)
        ).fetchone()

        if not db_row:
            skipped += 1
            continue

        registered_code = db_row[0]

        # 다음 종목 헤더까지가 이 종목 블록
        next_hr = header_rows[idx + 1] if idx + 1 < len(header_rows) else len(raw)

        batch = []
        for r in range(hr + 1, next_hr):
            yr_val = raw.iloc[r, 6]
            try:
                yr = int(float(yr_val))
                if not (2000 <= yr <= 2030):
                    continue
            except:
                continue

            # 연간 항목 저장
            for item_name, col_idx in ANNUAL_COLS.items():
                val = safe_float(raw.iloc[r, col_idx])
                if val is not None:
                    batch.append((registered_code, yr, 0, item_name, val, "EXCEL"))

            # 분기 항목 저장
            for item_name, (c1, c2, c3, c4) in QUARTER_COLS.items():
                for q, ci in enumerate([c1, c2, c3, c4], start=1):
                    val = safe_float(raw.iloc[r, ci])
                    if val is not None:
                        batch.append((registered_code, yr, q, item_name, val, "EXCEL"))

        if batch:
            conn.executemany("""
                INSERT INTO financials (stock_code, year, quarter, item, value, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(stock_code, year, quarter, item)
                DO UPDATE SET value=excluded.value, source=excluded.source, updated_at=excluded.updated_at
            """, batch)
            conn.commit()
            total_rows += len(batch)

        if (idx + 1) % 50 == 0 or idx + 1 == len(header_rows):
            print(f"  진행: {idx+1}/{len(header_rows)} 종목 | 저장: {total_rows:,}행")

    conn.close()
    print(f"\n완료!")
    print(f"  저장된 데이터: {total_rows:,}행")
    print(f"  DB 미등록으로 건너뜀: {skipped}개 종목")
    print(f"\n이제 앱에서 DB 데이터를 바로 사용할 수 있습니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="EPS-ACCUM.xlsx")
    args = parser.parse_args()
    migrate(args.file)
