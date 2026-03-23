"""
SQLAlchemy를 사용하여 식약처 API 데이터를 foods 테이블에 시드하는 스크립트.
Django seed.py로 이미 시드한 경우 이 스크립트는 실행할 필요가 없다.
동일한 DB(foodcommit)를 사용하므로 둘 중 하나만 실행하면 된다.

환경변수:
  - DATA_GO_KR_API_KEY: 공공데이터포털 서비스키 (필수)
"""
import os
import sys
import time
import asyncio
import requests

from sqlalchemy import select, func
from database import async_session
from models import Food


API_URL = "https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo02/getFoodNtrCpntDbInq02"
NUM_OF_ROWS = 1000


def fetch_page(service_key: str, page_no: int) -> dict:
    params = {
        "serviceKey": service_key,
        "type": "json",
        "numOfRows": NUM_OF_ROWS,
        "pageNo": page_no,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _float_or_none(value) -> float | None:
    if not value or not str(value).strip():
        return None
    try:
        return float(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def parse_item(item: dict) -> dict:
    return {
        "food_code": item.get("FOOD_CD", "").strip(),
        "food_name": item.get("FOOD_NM_KR", "").strip(),
        "data_type": item.get("DB_GRP_NM", "").strip(),
        "energy_kcal": _float_or_none(item.get("AMT_NUM1")),
        "water_g": _float_or_none(item.get("AMT_NUM2")),
        "protein_g": _float_or_none(item.get("AMT_NUM3")),
        "fat_g": _float_or_none(item.get("AMT_NUM5")),
        "carbohydrate_g": _float_or_none(item.get("AMT_NUM6")),
        "sugar_g": _float_or_none(item.get("AMT_NUM7")),
        "fiber_g": _float_or_none(item.get("AMT_NUM8")),
        "calcium_mg": _float_or_none(item.get("AMT_NUM11")),
        "sodium_mg": _float_or_none(item.get("AMT_NUM13")),
        "vitamin_c_mg": None,
        "source_name": item.get("SUB_REF_NAME", "").strip() or None,
    }


async def seed():
    service_key = os.environ.get("DATA_GO_KR_API_KEY")
    if not service_key:
        print("ERROR: DATA_GO_KR_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    async with async_session() as session:
        result = await session.execute(select(func.count()).select_from(Food))
        count = result.scalar()
        if count > 0:
            print(f"이미 {count}건의 데이터가 존재합니다. 시드를 건너뜁니다.")
            return

    data = fetch_page(service_key, 1)
    total_count = data["body"]["totalCount"]
    total_pages = (total_count + NUM_OF_ROWS - 1) // NUM_OF_ROWS
    print(f"총 {total_count}건, {total_pages}페이지 수집 시작...")

    total_inserted = 0
    for page_no in range(1, total_pages + 1):
        if page_no > 1:
            data = fetch_page(service_key, page_no)
            time.sleep(0.1)

        items = data["body"].get("items", [])
        if not items:
            break

        async with async_session() as session:
            session.add_all([Food(**parse_item(item)) for item in items])
            await session.commit()

        total_inserted += len(items)
        print(f"  [{page_no}/{total_pages}] {total_inserted}/{total_count}건 완료")

    print(f"시드 완료: 총 {total_inserted}건")


if __name__ == "__main__":
    asyncio.run(seed())
