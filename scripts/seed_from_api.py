"""
식약처 식품영양성분DB API에서 데이터를 수집하여 foods 테이블에 시드하는 스크립트.
프로젝트 루트에서 실행: python scripts/seed_from_api.py

환경변수:
  - DATA_GO_KR_API_KEY: 공공데이터포털 서비스키 (필수)
  - DATABASE_URL: PostgreSQL 접속 URL (기본: postgresql://postgres:postgres@localhost:5432/foodcommit)
"""
import os
import sys
import time
import requests
import psycopg2
from psycopg2.extras import execute_values

API_URL = "https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo02/getFoodNtrCpntDbInq02"
NUM_OF_ROWS = 100  # 페이지당 최대 건수 (API 제한: 최대 100)


def fetch_page(service_key: str, page_no: int) -> dict:
    """API에서 한 페이지 데이터를 가져온다."""
    params = {
        "serviceKey": service_key,
        "type": "json",
        "numOfRows": str(NUM_OF_ROWS),
        "pageNo": str(page_no),
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_item(item: dict) -> tuple:
    """API 응답 item을 DB insert용 tuple로 변환한다."""
    return (
        item.get("FOOD_CD", "").strip(),
        item.get("FOOD_NM_KR", "").strip(),
        item.get("DB_GRP_NM", "").strip(),
        _float_or_none(item.get("AMT_NUM1")),   # energy_kcal
        _float_or_none(item.get("AMT_NUM2")),   # water_g
        _float_or_none(item.get("AMT_NUM3")),   # protein_g
        _float_or_none(item.get("AMT_NUM5")),   # fat_g
        _float_or_none(item.get("AMT_NUM6")),   # carbohydrate_g
        _float_or_none(item.get("AMT_NUM7")),   # sugar_g
        _float_or_none(item.get("AMT_NUM8")),   # fiber_g
        _float_or_none(item.get("AMT_NUM11")),  # calcium_mg
        _float_or_none(item.get("AMT_NUM13")),  # sodium_mg
        None,                                    # vitamin_c_mg (매핑 확인 필요)
        item.get("SUB_REF_NAME", "").strip() or None,  # source_name
    )


def _float_or_none(value):
    if not value or not str(value).strip():
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def seed():
    service_key = os.environ.get("DATA_GO_KR_API_KEY")
    if not service_key:
        print("ERROR: DATA_GO_KR_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/foodcommit")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # 이미 데이터가 있으면 건너뜀 (멱등성)
    cur.execute("SELECT COUNT(*) FROM foods")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"이미 {count}건의 데이터가 존재합니다. 시드를 건너뜁니다.")
        conn.close()
        return

    # 첫 페이지로 totalCount 확인
    data = fetch_page(service_key, 1)
    total_count = data["body"]["totalCount"]
    total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    print(f"총 {total_count}건, {total_pages}페이지 수집 시작...")

    insert_sql = """
        INSERT INTO foods (
            food_code, food_name, data_type,
            energy_kcal, water_g, protein_g, fat_g,
            carbohydrate_g, sugar_g, fiber_g,
            calcium_mg, sodium_mg, vitamin_c_mg, source_name
        ) VALUES %s
    """

    total_inserted = 0
    for page_no in range(1, total_pages + 1):
        if page_no > 1:
            data = fetch_page(service_key, page_no)
            time.sleep(0.1)  # API rate limit 배려

        items = data["body"].get("items", [])
        if not items:
            break

        rows = [parse_item(item) for item in items]
        execute_values(cur, insert_sql, rows)
        conn.commit()

        total_inserted += len(rows)
        print(f"  [{page_no}/{total_pages}] {total_inserted}/{total_count}건 완료")

    conn.close()
    print(f"시드 완료: 총 {total_inserted}건")


if __name__ == "__main__":
    seed()
