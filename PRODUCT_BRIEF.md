# Django Ninja vs FastAPI 성능 벤치마크 기획서

## 1. 목적

Django Ninja(동기, Gunicorn) vs FastAPI(비동기, Uvicorn) 환경에서 워커 수와 작업 유형에 따른 성능 차이를 정량적으로 측정하고, 차트로 시각화하여 비교한다. 두 프레임워크 모두 Pydantic 기반 스키마를 사용하여 직렬화/역직렬화 조건을 동일하게 맞춘다.


## 2. 테스트 대상 서버 구성

| 구성 ID | 프레임워크 | WSGI/ASGI | 워커 수 | 비고 |
|---------|-----------|-----------|--------|------|
| `django-4w` | Django Ninja + Gunicorn (sync worker) | WSGI | 4 | |
| `django-32w` | Django Ninja + Gunicorn (sync worker) | WSGI | 32 | |
| `fastapi-2w` | FastAPI + Uvicorn | ASGI | 2 | |
| `fastapi-4w` | FastAPI + Uvicorn | ASGI | 4 | |
| `fastapi-4w-sync` | FastAPI + Uvicorn | ASGI | 4 | Phase 1 CPU Bound 전용, `def` 핸들러 |
| `fastapi-4w-async` | FastAPI + Uvicorn | ASGI | 4 | Phase 1 CPU Bound 전용, `async def` 핸들러 |

워커 구성은 `config.yaml` 등에서 자유롭게 추가/삭제할 수 있도록 설계한다.
앱 컨테이너는 **AWS t3.medium 기준(vCPU 2, Memory 4GB)**으로 리소스를 제한하여 실제 운영 환경과 유사한 조건에서 테스트한다.


## 3. 벤치마크 2단계 구조

### Phase 1 — 합성 벤치마크

CPU/IO/Mixed 시나리오로 프레임워크의 본질적 특성을 비교한다.

#### 3-1. CPU Bound
- 피보나치 수열 계산, 소수 판별 등 순수 연산 작업
- 예: `GET /benchmark/cpu` → fib(30) 계산 후 결과 반환
- **참여 구성**: django-4w, django-32w, fastapi-2w, fastapi-4w-sync, fastapi-4w-async
  - fastapi-4w는 sync/async 변형(fastapi-4w-sync, fastapi-4w-async)으로 대체하여 이 시나리오에서 제외
  - `fastapi-4w-sync`: CPU 핸들러를 `def`로 정의 → FastAPI가 자동으로 threadpool(`run_in_executor`)에서 실행, 이벤트 루프 비블로킹
  - `fastapi-4w-async`: CPU 핸들러를 `async def`로 정의 → 이벤트 루프에서 직접 실행, 블로킹 발생

#### 3-2. IO Bound
- 외부 API 호출 또는 `asyncio.sleep` / `time.sleep`으로 네트워크 지연 시뮬레이션
- 예: `GET /benchmark/io` → 100ms sleep 후 응답
- **참여 구성**: django-4w, django-32w, fastapi-2w, fastapi-4w (워커 수 스케일링 vs async 이점 비교)

#### 3-3. Mixed (CPU 50% + IO 50%)
- 하나의 요청 안에서 CPU 연산과 IO 대기를 절반씩 수행
- 예: `GET /benchmark/mixed` → fib(25) + 50ms sleep
- **참여 구성**: django-4w, django-32w, fastapi-2w, fastapi-4w (CPU 비중 섞일 때 async 이점 희석 정도 확인)

### Phase 2 — Real API 벤치마크

실제 DB 연동 API로 현실적인 워크로드를 비교한다.

**참여 구성**: 전체 4개 (django-4w, django-32w, fastapi-2w, fastapi-4w)

#### 3-4. Real Simple (단순 페이지네이션 조회)
- `GET /api/foods?page=1&size=20` — 단순 목록 조회
- 프레임워크 + ORM 오버헤드 순수 비교

#### 3-5. Real Heavy (복합 쿼리)
- `GET /api/foods/search?min_energy=100&max_energy=500&data_type=음식&sort=protein_g&page=1&size=20`
- 복합 필터 + 정렬 — DB 대기 시간이 길어질 때 async 이점 확인

#### 커넥션 풀
- 각 프레임워크의 기본 커넥션 관리 방식을 그대로 사용
  - Django: `CONN_MAX_AGE=None`(persistent connection) — 워커당 1커넥션 유지, 총 커넥션 수 = 워커 수
  - FastAPI: SQLAlchemy async `pool_size=5`, `max_overflow=10` (기본값) — 이벤트 루프 기반 풀링
  - 동작 모델이 본질적으로 다르므로 숫자를 억지로 맞추기보다 각 프레임워크의 권장 설정으로 비교

#### 공통 Pydantic Schema (shared_schemas/)

```python
# shared_schemas/food.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM mode (Django ORM, SQLAlchemy 둘 다 호환)

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

Django Ninja와 FastAPI 모두 이 스키마를 import하여 사용하므로 직렬화/검증 로직이 완전히 동일하다.

#### 음식 DB 스펙
- **시드 데이터 소스**: 식약처 식품영양성분DB — 음식 카테고리 19,495건, 성분 149개
  - 다운로드: 공공데이터포털 CSV (https://www.data.go.kr/data/15100070/standard.do)
  - 또는 식약처 Open API (https://various.foodsafetykorea.go.kr/nutrient/)
- 테이블: `foods` — 식품코드, 식품명, 카테고리, 에너지(kcal), 단백질, 지방, 탄수화물, 나트륨, 당류 등 주요 영양성분 컬럼으로 구성
- CSV 파일은 **git에 포함하지 않음** — `scripts/download_data.sh`로 공공데이터포털에서 다운로드
- `seed.py`에서 CSV 파싱 → DB insert


## 4. 부하 테스트 도구

**k6** (Grafana Labs, Go 기반) — 클라이언트 오버헤드가 낮고, CSV 출력을 네이티브 지원

k6는 **별도 Docker 컨테이너**로 실행하여 앱 서버와 리소스 경쟁을 방지한다. (리소스 제한 없음 — 충분한 부하 생성이 목적)

### 결과 출력
- k6 JSON 출력: `k6 run --out json=results/phase1/raw/cpu_bound_django-4w.json script.js`
- docker stats 모니터링은 CSV로 직접 기록
- **후처리 집계**: k6 raw JSON을 파싱하여 **1초 단위로 집계**(RPS, P50/P95/P99, 에러율)한 대시보드용 CSV를 별도 생성한다. JSON은 CSV 대비 후처리가 가볍고, k6 네이티브 메트릭 구조를 그대로 활용할 수 있다. 원본 raw JSON은 보관하되, 대시보드는 집계 CSV만 읽는다.

### 테스트 파라미터
| 항목 | 기본값 | 비고 |
|------|-------|------|
| 테스트 시간 | 40초 | `--duration` 옵션으로 변경 가능 |
| 동시 사용자 수 (VUs) | 100 | 시나리오별 조정 가능 |
| Ramp-up | 10초간 0→100 VUs | 점진적 부하 증가 |
| 대기 시간 | 0 (no wait) | 최대 RPS 측정 목적 |


## 5. 측정 지표

| 지표 | 설명 |
|-----|------|
| **RPS** (Requests Per Second) | 초당 처리 요청 수 |
| **Latency P50** | 응답 시간 중앙값 (ms) |
| **Latency P95** | 응답 시간 상위 5% (ms) |
| **Latency P99** | 응답 시간 상위 1% (ms) — tail latency, sync vs async 차이가 극명 |
| **Error Rate (%)** | 요청 실패율 — HTTP 200 이외 모든 응답(4xx, 5xx, 타임아웃 포함)을 에러로 집계. 200 응답은 body 내용과 무관하게 정상 처리로 간주 |
| **CPU Usage (%)** | 테스트 중 서버 프로세스 CPU 사용률 |
| **Memory Usage (MB)** | 테스트 중 서버 프로세스 메모리 사용량 |

CPU/Memory는 `docker stats` API로 1초 간격 샘플링하여 CSV에 기록. (컨테이너 환경에서 cgroup 리소스 제한을 정확히 반영)

> **시간 동기화**: k6 실행 직전에 epoch timestamp를 기록하고, docker stats 수집 스크립트도 동일한 epoch 기준으로 타임스탬프를 찍는다. 후처리 시 이 공통 epoch를 기준으로 elapsed time(0초~)을 정규화하여 k6 메트릭과 docker stats를 동일 시간축에 정렬한다.

> **Phase 2 추가 지표**: DB 컨테이너(PostgreSQL)의 CPU Usage(%), Memory Usage(MB)도 함께 수집하여 DB 병목 여부를 모니터링한다.


## 6. 실행 흐름

### 공통 실행 흐름 (Phase 1 / Phase 2 동일)
```
run_benchmark.py phase1|phase2

1. results/<phase>/ 전체 삭제 후 재생성 (멱등성 보장)
2. DB 시드 확인 (Phase 2만 해당 — 기존 my-postgres 컨테이너 사용)
3. 앱 컨테이너 기동 (환경변수로 워커 수 주입, 예: WORKERS=4)
4. 워밍업 요청 (5초)
5. k6 부하 테스트 실행 (40초) → raw CSV에 메트릭 기록
   └─ 동시에 docker stats 모니터 → CSV에 CPU/Memory 기록
6. 테스트 종료
7. 앱 컨테이너 종료
8. 다음 구성/시나리오로 반복 (3~7)
9. 후처리: raw CSV → 1초 단위 집계 CSV 생성, elapsed time(0~40초) 정규화
→ results/<phase>/ 에 CSV 생성
```

### 시각화
```
streamlit run dashboard.py
→ results/phase1/ + results/phase2/ CSV를 합쳐서 차트 표시
```

자동화 스크립트(`run_benchmark.py`)로 phase1, phase2를 각각 또는 전체를 한 번에 실행할 수 있어야 한다.


## 7. 결과물: 차트 시각화 (Streamlit)

벤치마크 완료 후 `results/` 디렉토리의 CSV를 읽어 **Streamlit 웹앱**으로 시각화한다.
`streamlit run dashboard.py`로 실행하면 브라우저에서 Phase 1 + Phase 2 결과가 바로 표시된다.

사이드바에서 시나리오 선택 시, 해당 시나리오의 참여 구성만으로 차트가 세로로 배치:

**Phase 1 시나리오 (CPU Bound / IO Bound / Mixed) — 5개 차트**:
1. **RPS** — 시계열 라인 차트 (초당 요청 수)
2. **Latency (P50, P95, P99)** — 시계열 라인 차트 (ms)
3. **Error Rate** — 시계열 라인 차트 (%)
4. **CPU Usage** — 시계열 라인 차트 (%)
5. **Memory Usage** — 시계열 라인 차트 (MB)

**Phase 2 시나리오 (Real Simple / Heavy) — 7개 차트**:
1. **RPS** — 시계열 라인 차트 (초당 요청 수)
2. **Latency (P50, P95, P99)** — 시계열 라인 차트 (ms)
3. **Error Rate** — 시계열 라인 차트 (%)
4. **CPU Usage** — 시계열 라인 차트 (%)
5. **Memory Usage** — 시계열 라인 차트 (MB)
6. **DB CPU Usage** — 시계열 라인 차트 (%)
7. **DB Memory Usage** — 시계열 라인 차트 (MB)

각 차트에 서버 구성(django-4w, django-32w, fastapi-2w, fastapi-4w 등)이 별도 라인으로 표시.
Plotly의 `shared_xaxes`를 사용하여 하나의 차트를 드래그 줌하면 나머지도 동시에 줌인.
X축은 elapsed time (0초~40초)으로 정규화.

### 차트 스타일
- 색상: Django 계열은 녹색 톤, FastAPI 계열은 파란색 톤
- Streamlit 기본 테마(다크/라이트 모드 자동 지원)


## 8. 프로젝트 구조 (예상)

```
benchmark_api/
├── PRODUCT_BRIEF.md          # 이 문서
├── config.yaml               # 서버 구성, 테스트 파라미터 설정
├── shared_schemas/           # 양쪽 앱이 공유하는 Pydantic 스키마
│   ├── __init__.py
│   └── food.py               # FoodOut, FoodListParams, FoodListResponse
├── django_app/
│   ├── Dockerfile
│   ├── manage.py
│   ├── app/
│   │   ├── models.py         # Food Django ORM 모델
│   │   ├── api.py            # Django Ninja router (Pydantic schema 사용)
│   │   └── urls.py
│   ├── benchmark/
│   │   └── api.py            # CPU/IO/Mixed 벤치마크 엔드포인트 (Ninja)
│   ├── seed.py               # DB 시드 스크립트
│   └── requirements.txt
├── fastapi_app/
│   ├── Dockerfile
│   ├── main.py               # FastAPI 앱 + 라우터 등록
│   ├── models.py             # SQLAlchemy 모델
│   ├── database.py           # async DB 세션
│   ├── routers/
│   │   ├── foods.py          # Real API 엔드포인트 (Pydantic schema 사용)
│   │   └── benchmark.py      # CPU/IO/Mixed 벤치마크 엔드포인트
│   ├── seed.py
│   └── requirements.txt
├── k6/
│   ├── cpu_bound.js
│   ├── io_bound.js
│   ├── mixed.js
│   ├── real_simple.js
│   └── real_heavy.js
├── scripts/
│   ├── run_benchmark.py      # 전체 자동화 (phase1/phase2 선택 실행)
│   └── download_data.sh      # 식약처 CSV 다운로드 스크립트
├── dashboard.py              # Streamlit 대시보드 (phase1 + phase2 CSV 읽어서 시각화)
├── docker-compose.yml        # 앱 서버 + k6
│                              #   - django_app: Gunicorn (cpus: 2, mem_limit: 4GB, t3.medium 기준)
│                              #   - fastapi_app: Uvicorn (cpus: 2, mem_limit: 4GB, t3.medium 기준)
│                              #   - k6: 부하 테스트 컨테이너 (리소스 제한 없음)
│                              #   * DB는 기존 my-postgres 컨테이너(foodcommit DB) 사용 — compose에 미포함
├── data/                      # .gitignore 처리 — download_data.sh로 생성
│   └── foods.csv             # 식약처 식품영양성분DB CSV (시드 데이터)
└── results/                  # 벤치마크 결과 CSV
    ├── phase1/               # 실행 시마다 전체 삭제 후 재생성
    │   ├── raw/              # k6 원본 JSON (요청별 개별 행)
    │   │   ├── cpu_bound_django-4w.json
    │   │   ├── cpu_bound_fastapi-4w-sync.json
    │   │   └── ...
    │   ├── cpu_bound_django-4w.csv          # 1초 단위 집계 CSV (대시보드용)
    │   ├── cpu_bound_fastapi-4w-sync.csv
    │   ├── stats_cpu_bound_django-4w.csv    # docker stats (CPU/Memory)
    │   └── ...
    └── phase2/               # 실행 시마다 전체 삭제 후 재생성
        ├── raw/              # k6 원본 JSON
        │   ├── real_simple_django-4w.json
        │   └── ...
        ├── real_simple_django-4w.csv        # 1초 단위 집계 CSV (대시보드용)
        ├── real_heavy_fastapi-4w.csv
        ├── stats_real_simple_django-4w.csv  # docker stats (앱 + DB)
        └── ...
```


## 9. 설정 가능 항목 (config.yaml)

```yaml
test_duration: 40        # 초
concurrent_users: 100
rampup_seconds: 10           # k6 stages: 0→VUs 도달 시간
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

# Phase 1 시나리오 (실행 시마다 전체 삭제 후 재생성)
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

# Phase 2 시나리오 (반복 실행, 매번 CSV 재생성)
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


## 10. 기술 스택

| 용도 | 기술 |
|-----|------|
| 동기 서버 | Django 4.x + Django Ninja + Gunicorn (sync worker) |
| 비동기 서버 | FastAPI + Uvicorn |
| API 스키마 | Pydantic v2 (양쪽 공통) |
| DB | PostgreSQL (`my-postgres` 컨테이너, `foodcommit` DB, port 5432) |
| ORM | Django ORM / SQLAlchemy (async) |
| 부하 테스트 | k6 (Grafana Labs) |
| 결과 저장 | CSV (k6 --out csv + docker stats 스크립트) |
| 시각화 | Streamlit + Plotly (인터랙티브 대시보드) |
| 모니터링 | docker stats API → CSV |
| 시드 데이터 | 식약처 식품영양성분DB (음식 19,495건, CSV) |
| 인프라 | Docker Compose (앱 서버 + k6) + 기존 my-postgres 컨테이너 |
| 자동화 | Python script + subprocess |

### 테스트 환경 요구사항

| 항목 | 버전 |
|------|------|
| Docker Engine | 24.x 이상 |
| Docker Compose | v2.20 이상 (Compose V2) |
| Python | 3.11+ (자동화 스크립트, Streamlit) |
| k6 | v0.47+ |
| Host OS | macOS 또는 Linux (ARM64/AMD64) |
