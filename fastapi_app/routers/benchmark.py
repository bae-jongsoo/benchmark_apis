import os
import sys
import time
import asyncio
from fastapi import APIRouter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_schemas.food import FoodOut, FoodListResponse

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
        result = fib(25)
        return {"result": result}
else:
    @router.get("/cpu")
    def cpu_bound():
        """CPU Bound (def): threadpool 실행"""
        result = fib(25)
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


# ===== Fake IO (DB 시뮬레이션) =====
_DUMMY_FOODS = [
    FoodOut(
        food_code=f"D{i:05d}", food_name=f"테스트식품{i}",
        data_type="일반", energy_kcal=100.0 + i, water_g=80.0,
        protein_g=10.0, fat_g=5.0, carbohydrate_g=20.0,
        sugar_g=3.0, fiber_g=2.0, calcium_mg=50.0,
        sodium_mg=200.0, vitamin_c_mg=10.0, source_name="테스트",
    )
    for i in range(20)
]


@router.get("/fake-io")
async def fake_io():
    """Fake IO: 5ms async sleep + Pydantic 직렬화 (DB 시뮬레이션)"""
    await asyncio.sleep(0.005)
    return FoodListResponse(
        items=_DUMMY_FOODS,
        total=1000,
        page=1,
        size=20,
    )
