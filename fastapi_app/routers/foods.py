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
