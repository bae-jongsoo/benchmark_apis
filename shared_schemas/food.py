from pydantic import BaseModel, ConfigDict

class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    food_code: str             # 식품코드
    food_name: str             # 식품명
    data_type: str             # 데이터구분명
    energy_kcal: float | None  # 에너지(kcal)
    water_g: float | None      # 수분(g)
    protein_g: float | None    # 단백질(g)
    fat_g: float | None        # 지방(g)
    carbohydrate_g: float | None  # 탄수화물(g)
    sugar_g: float | None      # 당류(g)
    fiber_g: float | None      # 식이섬유(g)
    calcium_mg: float | None   # 칼슘(mg)
    sodium_mg: float | None    # 나트륨(mg)
    vitamin_c_mg: float | None # 비타민C(mg)
    source_name: str | None    # 출처명

class FoodListParams(BaseModel):
    page: int = 1
    size: int = 20
    data_type: str | None = None  # 데이터구분명 필터

class FoodListResponse(BaseModel):
    items: list[FoodOut]
    total: int
    page: int
    size: int
