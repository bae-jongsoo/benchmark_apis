# 03. FastAPI 앱 구현

## 목표
FastAPI + Uvicorn 기반의 비동기 웹 서버를 구현한다. Phase 1 합성 벤치마크 엔드포인트(CPU/IO/Mixed)와 Phase 2 Real API 엔드포인트(Foods 목록/검색)를 모두 포함한다. CPU Bound 시나리오에서는 `CPU_HANDLER` 환경변수에 따라 sync/async 핸들러를 선택한다.

## 선행 태스크
- 01-project-setup (shared_schemas, config.yaml, docker-compose.yml이 완료된 상태)

## 구현할 파일 목록

### 1. `fastapi_app/requirements.txt`
```
fastapi>=0.104
uvicorn[standard]>=0.24
sqlalchemy[asyncio]>=2.0
asyncpg>=0.29
pydantic>=2.0
```

### 2. `fastapi_app/Dockerfile`

docker-compose.yml에서 build context가 프로젝트 루트(`.`)로, dockerfile이 `fastapi_app/Dockerfile`로 설정되어 있으므로, COPY 경로는 프로젝트 루트 기준이다.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY fastapi_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared_schemas /app/shared_schemas
COPY fastapi_app/ /app/

CMD uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WORKERS:-4}
```

### 3. `fastapi_app/database.py` — 비동기 DB 세션
```python
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "foodcommit")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,       # 기본값 — 기획서 스펙
    max_overflow=10,   # 기본값 — 기획서 스펙
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session
```

### 4. `fastapi_app/models.py` — SQLAlchemy 모델
```python
from sqlalchemy import Column, String, Float, BigInteger, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Food(Base):
    __tablename__ = "foods"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    food_code = Column(String(20), unique=True, nullable=False)
    food_name = Column(String(200), nullable=False)
    data_type = Column(String(50), nullable=False)
    energy_kcal = Column(Float, nullable=True)
    water_g = Column(Float, nullable=True)
    protein_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    carbohydrate_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    fiber_g = Column(Float, nullable=True)
    calcium_mg = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    vitamin_c_mg = Column(Float, nullable=True)
    source_name = Column(String(200), nullable=True)

    __table_args__ = (
        Index("ix_foods_data_type", "data_type"),
        Index("ix_foods_energy_kcal", "energy_kcal"),
        Index("ix_foods_protein_g", "protein_g"),
    )
```

**주의**: Django가 마이그레이션으로 테이블을 생성하므로, FastAPI의 SQLAlchemy 모델은 동일한 `foods` 테이블을 참조만 한다. 테이블 생성은 하지 않는다.

### 5. `fastapi_app/routers/benchmark.py` — 합성 벤치마크 엔드포인트

```python
import os
import time
import asyncio
from fastapi import APIRouter

router = APIRouter(prefix="/benchmark")

CPU_HANDLER = os.environ.get("CPU_HANDLER", "sync")


def fib(n: int) -> int:
    """재귀 피보나치 (CPU 부하용)"""
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)


# ===== CPU Bound =====
# CPU_HANDLER 환경변수에 따라 sync/async 핸들러 등록
# - sync (기본): def 핸들러 → FastAPI가 threadpool에서 실행, 이벤트 루프 비블로킹
# - async: async def 핸들러 → 이벤트 루프에서 직접 실행, 블로킹 발생

if CPU_HANDLER == "async":
    @router.get("/cpu")
    async def cpu_bound():
        """CPU Bound (async def): 이벤트 루프 블로킹"""
        result = fib(30)
        return {"result": result}
else:
    @router.get("/cpu")
    def cpu_bound():
        """CPU Bound (def): threadpool 실행"""
        result = fib(30)
        return {"result": result}


# ===== IO Bound =====
@router.get("/io")
async def io_bound():
    """IO Bound: 100ms async sleep"""
    await asyncio.sleep(0.1)
    return {"result": "ok", "slept_ms": 100}


# ===== Mixed =====
@router.get("/mixed")
async def mixed():
    """Mixed: fib(25) + 50ms sleep
    CPU 연산은 이벤트 루프에서 실행 (의도적 — mixed 시나리오 특성)
    """
    result = fib(25)
    await asyncio.sleep(0.05)
    return {"result": result, "slept_ms": 50}
```

**핵심 포인트**:
- CPU Bound에서 `CPU_HANDLER` 환경변수로 sync/async 핸들러를 모듈 로드 시점에 결정
- `fastapi-4w-sync`: `def` → FastAPI가 자동으로 `run_in_executor`에서 실행 (이벤트 루프 비블로킹)
- `fastapi-4w-async`: `async def` → 이벤트 루프에서 직접 실행 (블로킹 발생)
- IO Bound: `asyncio.sleep` 사용 (비동기 sleep)
- Mixed: `fib(25)` + `asyncio.sleep(0.05)` — CPU 부분은 이벤트 루프에서 실행

### 6. `fastapi_app/routers/__init__.py`
빈 파일

### 7. `fastapi_app/routers/foods.py` — Real API 엔드포인트

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models import Food
from shared_schemas.food import FoodOut, FoodListResponse

router = APIRouter(prefix="/api")


@router.get("/foods", response_model=FoodListResponse)
async def food_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    data_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Real Simple: 단순 페이지네이션 조회"""
    query = select(Food)

    if data_type:
        query = query.where(Food.data_type == data_type)

    # 총 건수
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 페이지네이션
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return FoodListResponse(
        items=[FoodOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/foods/search", response_model=FoodListResponse)
async def food_search(
    min_energy: float | None = None,
    max_energy: float | None = None,
    data_type: str | None = None,
    sort: str = "food_name",
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Real Heavy: 복합 필터 + 정렬"""
    query = select(Food)

    if min_energy is not None:
        query = query.where(Food.energy_kcal >= min_energy)
    if max_energy is not None:
        query = query.where(Food.energy_kcal <= max_energy)
    if data_type:
        query = query.where(Food.data_type == data_type)

    # 정렬
    sort_columns = {
        "food_name": Food.food_name.asc(),
        "-food_name": Food.food_name.desc(),
        "energy_kcal": Food.energy_kcal.asc(),
        "-energy_kcal": Food.energy_kcal.desc(),
        "protein_g": Food.protein_g.asc(),
        "-protein_g": Food.protein_g.desc(),
        "fat_g": Food.fat_g.asc(),
        "-fat_g": Food.fat_g.desc(),
        "carbohydrate_g": Food.carbohydrate_g.asc(),
        "-carbohydrate_g": Food.carbohydrate_g.desc(),
    }
    order_clause = sort_columns.get(sort, Food.food_name.asc())
    query = query.order_by(order_clause)

    # 총 건수
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 페이지네이션
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    result = await db.execute(query)
    items = result.scalars().all()

    return FoodListResponse(
        items=[FoodOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
```

### 8. `fastapi_app/main.py` — FastAPI 앱 엔트리포인트
```python
from fastapi import FastAPI
from routers import benchmark, foods

app = FastAPI(title="FastAPI Benchmark")

app.include_router(benchmark.router)
app.include_router(foods.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

## 완료 기준
- `fastapi_app/` 디렉토리에 모든 파일이 존재한다
- FastAPI가 다음 6개 엔드포인트를 제공한다:
  - `GET /health` — 헬스체크
  - `GET /benchmark/cpu` — fib(30) 계산 (CPU_HANDLER에 따라 sync/async)
  - `GET /benchmark/io` — 100ms async sleep
  - `GET /benchmark/mixed` — fib(25) + 50ms async sleep
  - `GET /api/foods?page=1&size=20` — 단순 목록 조회
  - `GET /api/foods/search?min_energy=100&max_energy=500&data_type=음식&sort=protein_g&page=1&size=20` — 복합 검색
- `shared_schemas.food`의 Pydantic 스키마를 import하여 사용한다
- SQLAlchemy async로 DB 접근 (pool_size=5, max_overflow=10)
- Dockerfile이 Uvicorn으로 기동하며, `WORKERS` 환경변수로 워커 수를 조절한다
- `CPU_HANDLER` 환경변수로 CPU Bound 핸들러의 sync/async를 선택할 수 있다
- Dockerfile의 COPY 경로가 프로젝트 루트 기준이다 (Task 01에서 docker-compose.yml의 build context를 `.`으로 설정)
