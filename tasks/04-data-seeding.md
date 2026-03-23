# 04. API 데이터 수집 및 시드

## 목표
식품의약품안전처 식품영양성분DB API를 호출하여 데이터를 수집하고 PostgreSQL `foods` 테이블에 insert하는 시드 스크립트를 구현한다.

## 선행 태스크
- 01-project-setup (프로젝트 구조, config.yaml)
- 02-django-app (Django ORM 모델 — 마이그레이션으로 `foods` 테이블 생성)

## API 정보

- **엔드포인트**: `https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo02/getFoodNtrCpntDbInq02`
- **인증**: `serviceKey` 쿼리 파라미터 (공공데이터포털 발급 키)
- **총 데이터**: 약 275,856건
- **페이징 파라미터**: `pageNo`, `numOfRows` (최대 1000)
- **응답 형식**: `type=json`

### API 응답 구조
```json
{
  "header": { "resultCode": "00", "resultMsg": "NORMAL SERVICE." },
  "body": {
    "pageNo": 1,
    "totalCount": 275856,
    "numOfRows": 1000,
    "items": [
      {
        "FOOD_CD": "D101-004160000-0001",
        "FOOD_NM_KR": "국밥_돼지머리",
        "DB_GRP_NM": "음식",
        "AMT_NUM1": "137.000",
        "AMT_NUM2": "71.60",
        "AMT_NUM3": "6.70",
        "AMT_NUM5": "0.63",
        "AMT_NUM6": "15.94",
        "AMT_NUM7": "0.16",
        "AMT_NUM8": "0.70",
        "AMT_NUM11": "24.00",
        "AMT_NUM13": "181.000",
        "SUB_REF_NAME": "식품의약품안전처",
        ...
      }
    ]
  }
}
```

### API → DB 필드 매핑

| API 필드 | DB 필드 | 설명 |
|---------|---------|------|
| `FOOD_CD` | `food_code` | 식품코드 |
| `FOOD_NM_KR` | `food_name` | 식품명 |
| `DB_GRP_NM` | `data_type` | 데이터구분명 |
| `AMT_NUM1` | `energy_kcal` | 에너지(kcal) |
| `AMT_NUM2` | `water_g` | 수분(g) |
| `AMT_NUM3` | `protein_g` | 단백질(g) |
| `AMT_NUM5` | `fat_g` | 지방(g) |
| `AMT_NUM6` | `carbohydrate_g` | 탄수화물(g) |
| `AMT_NUM7` | `sugar_g` | 당류(g) |
| `AMT_NUM8` | `fiber_g` | 식이섬유(g) |
| `AMT_NUM11` | `calcium_mg` | 칼슘(mg) |
| `AMT_NUM13` | `sodium_mg` | 나트륨(mg) |
| `SUB_REF_NAME` | `source_name` | 출처명 |

> **참고**: `vitamin_c_mg` 필드에 해당하는 AMT_NUM 번호는 API 문서에서 확인 필요. 없으면 None 처리.

## 구현할 파일 목록

### 1. `scripts/seed_from_api.py` — API 기반 시드 스크립트 (독립 실행)

```python
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
NUM_OF_ROWS = 1000  # 페이지당 최대 건수


def fetch_page(service_key: str, page_no: int) -> dict:
    """API에서 한 페이지 데이터를 가져온다."""
    params = {
        "serviceKey": service_key,
        "type": "json",
        "numOfRows": NUM_OF_ROWS,
        "pageNo": page_no,
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


def _float_or_none(value) -> float | None:
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
```

### 2. `django_app/seed.py` — Django ORM 기반 시드 (API 호출)

```python
"""
Django ORM을 사용하여 식약처 API 데이터를 foods 테이블에 시드하는 스크립트.
프로젝트 루트에서 실행: python django_app/seed.py
또는 컨테이너 내부에서 실행: python seed.py

환경변수:
  - DATA_GO_KR_API_KEY: 공공데이터포털 서비스키 (필수)
"""
import os
import sys
import time
import requests
import django

# Django 설정 로드
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from app.models import Food

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


def parse_item(item: dict) -> Food:
    return Food(
        food_code=item.get("FOOD_CD", "").strip(),
        food_name=item.get("FOOD_NM_KR", "").strip(),
        data_type=item.get("DB_GRP_NM", "").strip(),
        energy_kcal=_float_or_none(item.get("AMT_NUM1")),
        water_g=_float_or_none(item.get("AMT_NUM2")),
        protein_g=_float_or_none(item.get("AMT_NUM3")),
        fat_g=_float_or_none(item.get("AMT_NUM5")),
        carbohydrate_g=_float_or_none(item.get("AMT_NUM6")),
        sugar_g=_float_or_none(item.get("AMT_NUM7")),
        fiber_g=_float_or_none(item.get("AMT_NUM8")),
        calcium_mg=_float_or_none(item.get("AMT_NUM11")),
        sodium_mg=_float_or_none(item.get("AMT_NUM13")),
        vitamin_c_mg=None,
        source_name=item.get("SUB_REF_NAME", "").strip() or None,
    )


def seed():
    service_key = os.environ.get("DATA_GO_KR_API_KEY")
    if not service_key:
        print("ERROR: DATA_GO_KR_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    if Food.objects.exists():
        count = Food.objects.count()
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

        foods = [parse_item(item) for item in items]
        Food.objects.bulk_create(foods)

        total_inserted += len(foods)
        print(f"  [{page_no}/{total_pages}] {total_inserted}/{total_count}건 완료")

    print(f"시드 완료: 총 {total_inserted}건")


if __name__ == "__main__":
    seed()
```

### 3. `fastapi_app/seed.py` — SQLAlchemy async 기반 시드 (API 호출)

```python
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
```

## 시드 전략
- `run_benchmark.py`에서 Phase 2 실행 전에 시드 확인을 수행한다
- Django의 `manage.py migrate`로 테이블을 생성한 뒤, `django_app/seed.py` 또는 `scripts/seed_from_api.py`로 데이터를 삽입한다
- Django와 FastAPI는 **동일한 DB**(my-postgres / foodcommit)를 사용하므로, 시드는 한 번만 실행하면 된다
- API rate limit 배려를 위해 페이지 간 0.1초 대기
- `numOfRows=1000`으로 약 276페이지 호출 필요 (전체 수집 예상 시간: 약 1~2분)

## 환경변수
- `DATA_GO_KR_API_KEY`: 공공데이터포털 서비스키 (필수). `.env` 파일 또는 docker-compose.yml의 environment에 설정.

## 완료 기준
- `scripts/seed_from_api.py`가 API를 호출하여 전체 데이터를 `foods` 테이블에 insert할 수 있다
- `django_app/seed.py`로도 API 기반 시드가 가능하다
- `fastapi_app/seed.py`로도 동일하게 시드할 수 있다 (대안)
- 이미 데이터가 있으면 중복 삽입하지 않는다 (멱등성)
- API 필드(AMT_NUM*)를 영문 모델 필드로 올바르게 매핑한다
- 숫자 필드의 콤마(,) 포함 값을 정상적으로 파싱한다 (예: "1,670.000" → 1670.0)
