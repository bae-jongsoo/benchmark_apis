# 02. Django Ninja 앱 구현

## 목표
Django Ninja 기반의 동기 웹 서버를 구현한다. Phase 1 합성 벤치마크 엔드포인트(CPU/IO/Mixed)와 Phase 2 Real API 엔드포인트(Foods 목록/검색)를 모두 포함한다.

## 선행 태스크
- 01-project-setup (shared_schemas, config.yaml, docker-compose.yml이 완료된 상태)

## 구현할 파일 목록

### 1. `django_app/requirements.txt`
```
django>=4.2,<5.0
django-ninja>=1.0
gunicorn>=21.2
psycopg2-binary>=2.9
pydantic>=2.0
```

### 2. `django_app/Dockerfile`

docker-compose.yml에서 build context가 프로젝트 루트(`.`)로, dockerfile이 `django_app/Dockerfile`로 설정되어 있으므로, COPY 경로는 프로젝트 루트 기준이다.

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY django_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared_schemas /app/shared_schemas
COPY django_app/ /app/

CMD gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${WORKERS:-4} \
    --timeout 120
```

### 3. `django_app/config/` — Django 프로젝트 설정

#### `django_app/config/__init__.py`
빈 파일

#### `django_app/config/settings.py`
```python
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = "benchmark-secret-key-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "app",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "foodcommit"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "CONN_MAX_AGE": None,  # persistent connection — 워커당 1커넥션 유지
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

- `CONN_MAX_AGE=None`: persistent connection 사용 (기획서 스펙)
- 불필요한 미들웨어, 앱 최소화 (벤치마크 목적)

#### `django_app/config/urls.py`
```python
from django.urls import path
from app.api import api

urlpatterns = [
    path("", api.urls),
]
```

#### `django_app/config/wsgi.py`
```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
```

### 4. `django_app/manage.py`
```python
#!/usr/bin/env python
import os
import sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
```

### 5. `django_app/app/` — Django 앱

#### `django_app/app/__init__.py`
빈 파일

#### `django_app/app/models.py` — Food Django ORM 모델
```python
from django.db import models

class Food(models.Model):
    food_code = models.CharField(max_length=20, unique=True)  # 식품코드
    food_name = models.CharField(max_length=200)               # 식품명
    data_type = models.CharField(max_length=50)                # 데이터구분명
    energy_kcal = models.FloatField(null=True, blank=True)     # 에너지(kcal)
    water_g = models.FloatField(null=True, blank=True)         # 수분(g)
    protein_g = models.FloatField(null=True, blank=True)       # 단백질(g)
    fat_g = models.FloatField(null=True, blank=True)           # 지방(g)
    carbohydrate_g = models.FloatField(null=True, blank=True)  # 탄수화물(g)
    sugar_g = models.FloatField(null=True, blank=True)         # 당류(g)
    fiber_g = models.FloatField(null=True, blank=True)         # 식이섬유(g)
    calcium_mg = models.FloatField(null=True, blank=True)      # 칼슘(mg)
    sodium_mg = models.FloatField(null=True, blank=True)       # 나트륨(mg)
    vitamin_c_mg = models.FloatField(null=True, blank=True)    # 비타민C(mg)
    source_name = models.CharField(max_length=200, null=True, blank=True)  # 출처명

    class Meta:
        db_table = "foods"
        indexes = [
            models.Index(fields=["data_type"]),
            models.Index(fields=["energy_kcal"]),
            models.Index(fields=["protein_g"]),
        ]

    def __str__(self):
        return f"{self.food_code} - {self.food_name}"
```

#### `django_app/app/api.py` — Django Ninja API 라우터

```python
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
    """CPU Bound: fib(30) 계산"""
    result = fib(30)
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
```

### 6. Django 마이그레이션
Dockerfile 또는 컨테이너 기동 시 `python manage.py migrate`를 실행해야 한다. 엔트리포인트 스크립트를 만들거나, `run_benchmark.py`에서 마이그레이션을 수행할 수 있다.

#### `django_app/entrypoint.sh`
```bash
#!/bin/bash
python manage.py migrate --noinput
exec "$@"
```

Dockerfile에 `ENTRYPOINT ["bash", "entrypoint.sh"]` 추가.

## 완료 기준
- `django_app/` 디렉토리에 모든 파일이 존재한다
- Django Ninja API가 다음 6개 엔드포인트를 제공한다:
  - `GET /health` — 헬스체크
  - `GET /benchmark/cpu` — fib(30) 계산
  - `GET /benchmark/io` — 100ms sleep
  - `GET /benchmark/mixed` — fib(25) + 50ms sleep
  - `GET /api/foods?page=1&size=20` — 단순 목록 조회
  - `GET /api/foods/search?min_energy=100&max_energy=500&data_type=음식&sort=protein_g&page=1&size=20` — 복합 검색
- `shared_schemas.food`의 Pydantic 스키마를 import하여 사용한다
- Dockerfile이 Gunicorn + sync worker로 기동하며, `WORKERS` 환경변수로 워커 수를 조절한다
- `CONN_MAX_AGE=None`으로 persistent connection을 사용한다
- Dockerfile의 COPY 경로가 프로젝트 루트 기준이다 (Task 01에서 docker-compose.yml의 build context를 `.`으로 설정)
