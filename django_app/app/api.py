import sys
import os
import time
import math

from ninja import NinjaAPI, Query

# shared_schemas 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_schemas.food import FoodOut, FoodListParams, FoodListResponse

from app.models import Food

api = NinjaAPI()


# ========== 헬스체크 ==========

@api.get("/health")
def health(request):
    return {"status": "ok"}


# ========== Phase 1: 합성 벤치마크 ==========

def fib(n: int) -> int:
    """재귀 피보나치 (CPU 부하용)"""
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)


@api.get("/benchmark/cpu")
def cpu_bound(request):
    """CPU Bound: fib(25) 계산"""
    result = fib(25)
    return {"result": result}


@api.get("/benchmark/io")
def io_bound(request):
    """IO Bound: 100ms sleep"""
    time.sleep(0.1)
    return {"result": "ok", "slept_ms": 100}


@api.get("/benchmark/mixed")
def mixed(request):
    """Mixed: fib(25) + 50ms sleep"""
    result = fib(25)
    time.sleep(0.05)
    return {"result": result, "slept_ms": 50}


# ========== Phase 2: Real API ==========

@api.get("/api/foods", response=FoodListResponse)
def food_list(request, params: Query[FoodListParams]):
    """Real Simple: 단순 페이지네이션 조회"""
    qs = Food.objects.all()

    if params.data_type:
        qs = qs.filter(data_type=params.data_type)

    total = qs.count()
    offset = (params.page - 1) * params.size
    items = list(qs[offset:offset + params.size])

    return FoodListResponse(
        items=[FoodOut.model_validate(item) for item in items],
        total=total,
        page=params.page,
        size=params.size,
    )


@api.get("/api/foods/search", response=FoodListResponse)
def food_search(
    request,
    min_energy: float = None,
    max_energy: float = None,
    data_type: str = None,
    sort: str = "food_name",
    page: int = 1,
    size: int = 20,
):
    """Real Heavy: 복합 필터 + 정렬"""
    qs = Food.objects.all()

    if min_energy is not None:
        qs = qs.filter(energy_kcal__gte=min_energy)
    if max_energy is not None:
        qs = qs.filter(energy_kcal__lte=max_energy)
    if data_type:
        qs = qs.filter(data_type=data_type)

    # 정렬 필드 허용 목록
    allowed_sort_fields = [
        "food_name", "-food_name",
        "energy_kcal", "-energy_kcal",
        "protein_g", "-protein_g",
        "fat_g", "-fat_g",
        "carbohydrate_g", "-carbohydrate_g",
    ]
    if sort in allowed_sort_fields:
        qs = qs.order_by(sort)
    else:
        qs = qs.order_by("food_name")

    total = qs.count()
    offset = (page - 1) * size
    items = list(qs[offset:offset + size])

    return FoodListResponse(
        items=[FoodOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )
