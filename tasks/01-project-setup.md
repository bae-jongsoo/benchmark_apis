# 01. 프로젝트 초기 설정

## 목표
프로젝트의 기반 구조를 생성한다. 공유 스키마, 설정 파일, Docker Compose 기본 구조, .gitignore 등을 세팅하여 이후 태스크에서 앱을 구현할 수 있는 토대를 만든다.

## 선행 태스크
없음 (첫 번째 태스크)

## 구현할 파일 목록

### 1. `config.yaml` — 벤치마크 설정 파일
서버 구성, 테스트 파라미터, 시나리오별 참여 구성을 정의한다.

```yaml
test_duration: 40        # 초
concurrent_users: 100
rampup_seconds: 10       # k6 stages: 0→VUs 도달 시간
warmup_seconds: 5

server_configs:
  - name: django-4w
    framework: django
    workers: 4
    port: 8001
  - name: django-32w
    framework: django
    workers: 32
    port: 8003
  - name: fastapi-2w
    framework: fastapi
    workers: 2
    port: 8011
  - name: fastapi-4w
    framework: fastapi
    workers: 4
    port: 8012
  # Phase 1 CPU Bound 전용 구성
  - name: fastapi-4w-sync
    framework: fastapi
    workers: 4
    port: 8013
    cpu_handler: sync           # def 핸들러 (threadpool)
  - name: fastapi-4w-async
    framework: fastapi
    workers: 4
    port: 8014
    cpu_handler: async          # async def 핸들러 (이벤트 루프 블로킹)

phase1_scenarios:
  cpu_bound:
    - django-4w
    - django-32w
    - fastapi-2w
    - fastapi-4w-sync
    - fastapi-4w-async
  io_bound:
    - django-4w
    - django-32w
    - fastapi-2w
    - fastapi-4w
  mixed:
    - django-4w
    - django-32w
    - fastapi-2w
    - fastapi-4w

phase2_scenarios:
  real_simple:
    - django-4w
    - django-32w
    - fastapi-2w
    - fastapi-4w
  real_heavy:
    - django-4w
    - django-32w
    - fastapi-2w
    - fastapi-4w
```

### 2. `shared_schemas/` — 공유 Pydantic 스키마

#### `shared_schemas/__init__.py`
```python
from .food import FoodOut, FoodListParams, FoodListResponse
```

#### `shared_schemas/food.py`
```python
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
```

### 3. `docker-compose.yml` — Docker Compose 기본 구조

```yaml
version: "3.8"

services:
  django_app:
    build:
      context: .
      dockerfile: django_app/Dockerfile
    environment:
      - WORKERS=${WORKERS:-4}
      - DB_HOST=host.docker.internal
      - DB_PORT=5432
      - DB_NAME=foodcommit
      - DB_USER=postgres
      - DB_PASSWORD=postgres
    ports:
      - "${APP_PORT:-8001}:8000"
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
    extra_hosts:
      - "host.docker.internal:host-gateway"

  fastapi_app:
    build:
      context: .
      dockerfile: fastapi_app/Dockerfile
    environment:
      - WORKERS=${WORKERS:-4}
      - CPU_HANDLER=${CPU_HANDLER:-sync}
      - DB_HOST=host.docker.internal
      - DB_PORT=5432
      - DB_NAME=foodcommit
      - DB_USER=postgres
      - DB_PASSWORD=postgres
    ports:
      - "${APP_PORT:-8011}:8000"
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 4G
    extra_hosts:
      - "host.docker.internal:host-gateway"

  k6:
    image: grafana/k6:latest
    volumes:
      - ./k6:/scripts
      - ./results:/results
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**주의사항**:
- DB는 기존 `my-postgres` 컨테이너를 사용하므로 compose에 포함하지 않는다.
- `host.docker.internal`을 통해 호스트의 PostgreSQL에 접근한다.
- 앱 서버에만 리소스 제한(cpus: 2, memory: 4G)을 적용한다 (t3.medium 기준).
- k6에는 리소스 제한을 두지 않는다.
- `run_benchmark.py`에서 환경변수(`WORKERS`, `APP_PORT`, `CPU_HANDLER`)를 주입하여 구성별로 컨테이너를 기동한다.

### 4. `.gitignore`
```
# Data
data/

# Results
results/

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Django
django_app/db.sqlite3
django_app/static/

# Environment
.env
```

### 5. 디렉토리 구조 생성
아래 빈 디렉토리들을 생성한다:
- `data/` (빈 디렉토리, .gitkeep 불필요 — .gitignore 처리)
- `results/phase1/raw/`
- `results/phase2/raw/`
- `django_app/`
- `fastapi_app/`
- `k6/`
- `scripts/`

## 완료 기준
- `config.yaml`이 기획서의 모든 서버 구성과 시나리오를 포함한다
- `shared_schemas/food.py`에 `FoodOut`, `FoodListParams`, `FoodListResponse`가 정의되어 있다
- `docker-compose.yml`에 django_app, fastapi_app, k6 서비스가 정의되어 있다
- `.gitignore`에 data/, results/ 등이 포함되어 있다
- 기본 디렉토리 구조가 생성되어 있다
