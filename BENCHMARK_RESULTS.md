# 벤치마크 결과 정리

- 날짜: 2026-04-02
- 컨테이너 제한: CPU 4코어, Memory 2GB
- DB: PostgreSQL 16 (foods 275,856건)
- 부하 도구: k6 (ramp-up 10s + steady 30s)

---

## 1. 측정 결과

### 1차 테스트 (1,000 VUs)

#### Phase 1 — CPU Bound (fib(25))

| 구성 | RPS | P50(ms) | P95(ms) | P99(ms) | CPU(%) | Mem(MB) | RPS/CPU% |
|---|---:|---:|---:|---:|---:|---:|---:|
| spring-4t | 22,969 | 42.8 | 55.3 | 66.4 | 387.5 | 263.5 | 59.3 |
| spring-default | 19,559 | 48.9 | 81.6 | 133.5 | 404.5 | 356.3 | 48.3 |
| django-4w | 931 | 1,071.4 | 1,080.8 | 1,082.2 | 402.8 | 130.6 | 2.3 |
| fastapi-4w-async | 851 | 688.2 | 751.9 | 19,059.6 | 402.4 | 246.1 | 2.1 |
| django-4w-gevent | 845 | 494.0 | 522.4 | 5,487.5 | 401.2 | 158.2 | 2.1 |
| django-4w-gthread | 833 | 1,183.1 | 1,436.7 | 1,627.0 | 398.8 | 161.4 | 2.1 |
| fastapi-4w | 819 | 1,155.3 | 1,810.9 | 1,860.9 | 403.3 | 275.9 | 2.0 |
| django-16w | 647 | 1,532.4 | 1,576.6 | 1,589.1 | 398.6 | 465.2 | 1.6 |
| fastapi-2w | 505 | 1,664.7 | 7,377.6 | 7,586.1 | 208.7 | 160.1 | 2.4 |

#### Phase 2 — IO Bound (100ms sleep)

| 구성 | RPS | P50(ms) | P95(ms) | P99(ms) | CPU(%) | Mem(MB) | RPS/CPU% |
|---|---:|---:|---:|---:|---:|---:|---:|
| django-4w-gevent | 9,808 | 101.4 | 103.1 | 105.6 | 125.6 | 174.6 | 78.1 |
| fastapi-4w | 9,672 | 101.7 | 110.1 | 124.3 | 89.6 | 260.6 | 107.9 |
| fastapi-2w | 9,528 | 102.9 | 116.2 | 128.8 | 84.4 | 154.5 | 112.9 |
| spring-default | 1,973 | 505.2 | 513.8 | 557.2 | 41.4 | 343.7 | 47.7 |
| django-4w-gthread | 1,945 | 401.4 | 1,192.6 | 1,210.4 | 94.2 | 160.9 | 20.6 |
| django-16w | 154 | 6,184.1 | 6,247.3 | 6,254.1 | 25.5 | 464.9 | 6.0 |
| django-4w | 39 | 17,880.0 | 18,141.4 | 18,147.5 | 7.1 | 129.8 | 5.5 |
| spring-4t | 39 | 17,912.5 | 18,185.9 | 18,195.1 | 9.2 | 246.5 | 4.2 |

#### Phase 3 — Fake IO (5ms sleep + JSON 직렬화)

| 구성 | RPS | P50(ms) | P95(ms) | P99(ms) | CPU(%) | Mem(MB) | RPS/CPU% |
|---|---:|---:|---:|---:|---:|---:|---:|
| spring-default | 36,524 | 26.2 | 32.8 | 44.7 | 214.0 | 409.4 | 170.7 |
| django-4w-gevent | 18,400 | 52.6 | 98.5 | 117.8 | 404.5 | 178.8 | 45.5 |
| django-4w-gthread | 13,061 | 74.9 | 94.7 | 104.3 | 387.5 | 177.6 | 33.7 |
| fastapi-4w | 10,668 | 93.7 | 125.4 | 141.1 | 360.0 | 265.6 | 29.6 |
| fastapi-2w | 6,828 | 152.9 | 184.0 | 192.6 | 181.1 | 157.8 | 37.7 |
| django-16w | 2,796 | 321.6 | 376.5 | 398.9 | 114.2 | 466.4 | 24.5 |
| spring-4t | 700 | 1,421.3 | 1,453.9 | 1,456.4 | 33.0 | 263.7 | 21.2 |
| django-4w | 649 | 1,538.7 | 1,575.7 | 1,578.8 | 73.0 | 130.1 | 8.9 |

### 2차 테스트 (5,000 VUs) — 과부하 한계 테스트

#### Phase 1 — CPU Bound (fib(25))

| 구성 | RPS | P50(ms) | P95(ms) | P99(ms) | Err% | CPU(%) | Mem(MB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| spring-default | 19,341 | 253.1 | 300.1 | 361.3 | 0.0 | 378.5 | 545.1 |
| spring-4t | 17,808 | 273.2 | 349.2 | 361.8 | 0.0 | 386.3 | 441.4 |
| fastapi-4w-async | 882 | 690.0 | 759.1 | 17,473.5 | 4.2 | 402.2 | 246.5 |
| fastapi-4w | 842 | 2,046.1 | 21,479.6 | 21,978.4 | 2.0 | 406.7 | 296.3 |
| django-4w | 794 | 2,853.4 | 3,958.2 | 5,362.0 | 5.7 | 326.7 | 157.4 |
| django-16w | 674 | 3,332.5 | 4,369.1 | 8,874.0 | 6.6 | 352.8 | 444.1 |
| fastapi-2w | 544 | 1,868.2 | 18,767.7 | 23,475.1 | 5.9 | 208.2 | 175.4 |

#### Phase 2 — IO Bound (100ms sleep)

| 구성 | RPS | P50(ms) | P95(ms) | P99(ms) | Err% | CPU(%) | Mem(MB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| fastapi-2w | 33,693 | 11.6 | 239.6 | 281.4 | 68.8 | 121.1 | 190.6 |
| fastapi-4w | 30,943 | 155.3 | 296.6 | 346.1 | 41.7 | 202.5 | 330.3 |
| django-16w | 227 | 9,928.8 | 12,819.0 | 14,516.1 | 13.9 | 19.1 | 443.6 |
| django-4w | 127 | 16,441.6 | 23,613.1 | 23,703.0 | 18.5 | 7.4 | 155.3 |
| spring-default | 1,978 | 2,501.8 | 2,535.3 | 2,541.9 | 0.0 | 37.2 | 540.3 |
| spring-4t | 39 | 23,369.6 | 23,766.1 | 23,768.2 | 0.0 | 9.5 | 336.4 |

#### Phase 3 — Fake IO (5ms sleep + JSON 직렬화)

| 구성 | RPS | P50(ms) | P95(ms) | P99(ms) | Err% | CPU(%) | Mem(MB) |
|---|---:|---:|---:|---:|---:|---:|---:|
| spring-default | 33,723 | 134.3 | 223.4 | 249.7 | 0.0 | 213.0 | 539.5 |
| fastapi-4w | 10,237 | 243.8 | 337.7 | 368.1 | 0.0 | 383.4 | 302.0 |
| fastapi-2w | 6,594 | 200.2 | 269.6 | 287.0 | 0.3 | 196.3 | 167.3 |
| django-16w | 1,501 | 1,972.1 | 2,788.5 | 6,908.8 | 29.0 | 52.6 | 445.7 |
| spring-4t | 691 | 6,666.2 | 6,719.5 | 6,724.4 | 0.0 | 24.7 | 413.9 |
| django-4w | 542 | 3,301.3 | 3,803.9 | 4,457.8 | 14.7 | 41.9 | 125.0 |

### 에러율 비교 (1,000 VUs → 5,000 VUs)

| 구성 | CPU Bound | IO Bound | Fake IO |
|---|---|---|---|
| spring-default | 0% → 0% | 0% → 0% | 0% → 0% |
| spring-4t | 0% → 0% | 0% → 0% | 0% → 0% |
| fastapi-4w | 0% → 2.0% | 0% → 41.7% | 0% → 0% |
| fastapi-2w | 0% → 5.9% | 0% → 68.8% | 0% → 0.3% |
| django-4w | 0% → 5.7% | 0% → 18.5% | 0% → 14.7% |
| django-16w | 0% → 6.6% | 0% → 13.9% | 0.8% → 29.0% |

※ 2차 테스트에는 gevent/gthread 구성 미포함.

---

## 2. 관측된 현상

숫자에서 읽히는 팩트만 나열.

- CPU-bound에서 Spring(Java)의 RPS가 Python 프레임워크 대비 약 25배 높다.
- CPU-bound에서 RPS/CPU% 효율도 Spring이 약 25배 높다. 같은 CPU를 쓰면서 처리량이 다르다.
- CPU-bound에서 gevent/gthread/sync 워커 타입 간 RPS 차이가 거의 없다 (845 / 833 / 931).
- IO-bound(100ms sleep)에서 `django-4w-gevent`(9,808)가 `fastapi-4w`(9,672)와 거의 동일하다.
- IO-bound에서 `django-4w-gthread`(1,945)는 `spring-default`(1,973)와 비슷한 수준이다.
- IO-bound에서 `spring-4t`(4스레드)과 `django-4w`(sync 4워커)의 RPS가 39로 동일하다.
- IO-bound에서 FastAPI 워커 수(2 vs 4)는 RPS에 거의 영향이 없다 (9,528 vs 9,672).
- Fake IO에서 `django-4w-gevent`(18,400)가 `fastapi-4w`(10,668)를 앞질렀다.
- Fake IO에서 `django-4w-gthread`(13,061)도 `fastapi-4w`(10,668)보다 높다.
- Fake IO에서 `spring-default`(36,524)가 여전히 1위.
- 메모리는 django-4w(sync)가 가장 적게 쓴다 (130MB). gevent/gthread도 160~179MB로 가벼운 편.
- 5,000 VUs에서 Spring은 전 시나리오 에러율 0%를 유지했다. `spring-4t`(4스레드)도 마찬가지.
- 5,000 VUs IO-bound에서 FastAPI의 에러율이 41~69%로 가장 높다. RPS 숫자 자체는 30,000 이상으로 높게 찍힌다.
- 5,000 VUs에서 Django(sync)는 Fake IO에서 가장 많이 무너졌다 (django-16w 29%, django-4w 14.7%).
- `fastapi-4w-async`의 P99가 1,000 VUs에서 이미 19초로 극단적으로 높다.

---

## 3. 추측되는 원인

아래는 소스코드 레벨에서 검증하지 않은 추측임.

- **Spring CPU 25배 차이**: JVM JIT 컴파일러가 fib() 같은 반복 호출을 네이티브 코드로 최적화하는 반면, Python은 인터프리터로 한 줄씩 실행하기 때문으로 추측.
- **IO-bound에서 async/gevent 모델이 동기 모델을 압도**: FastAPI(async)와 gevent는 sleep 대기 중에 다른 요청을 처리할 수 있고, 동기 모델은 스레드/워커가 sleep 동안 점유되어 동시 처리 수가 스레드 수로 제한되기 때문으로 추측.
- **gevent ≒ FastAPI (IO-bound)**: gevent가 time.sleep을 monkey-patch하여 비동기로 바꾸기 때문에, 결과적으로 FastAPI의 asyncio.sleep과 같은 효과를 내는 것으로 추측.
- **gevent > FastAPI (Fake IO)**: 짧은 IO(5ms)에서는 직렬화 비중이 커지는데, gevent는 직렬화를 greenlet 안에서 바로 실행하고, FastAPI는 이벤트 루프 + 코루틴 스케줄링 오버헤드가 있기 때문으로 추측.
- **gthread ≒ spring-default (IO-bound)**: 둘 다 스레드 풀 모델(gthread 50스레드, Tomcat 200스레드). 100ms sleep이면 50스레드로 초당 500, 200스레드로 초당 2,000이 이론 상한이고, 실측치(1,945 / 1,973)가 이에 가까움.
- **CPU-bound에서 워커 타입 무관**: CPU 연산은 GIL에 의해 한 번에 하나의 스레드/greenlet만 실행 가능하므로, 워커 타입을 바꿔도 효과가 없는 것으로 추측.
- **spring-4t ≒ django-4w (IO-bound)**: 둘 다 동기 모델이고 동시 처리 단위가 4개이므로, 언어 성능과 무관하게 IO 대기 시간이 병목이 되어 같은 결과가 나오는 것으로 추측.
- **Spring 에러 0% (과부하)**: Tomcat의 accept queue가 초과 요청을 대기열에 쌓아둔 뒤 스레드가 빌 때마다 처리하는 방식이라 추측. 응답은 느려지지만(P50: 23초) 요청 자체는 거절하지 않는 것으로 보임.
- **FastAPI 과부하 에러 41~69%**: async 모델이 요청을 거절하지 않고 모두 받아들이지만, 동시에 처리하려다 리소스 한계에 부딪혀 응답 자체가 실패하는 것으로 추측.
- **Django 과부하 에러**: Gunicorn의 backlog 큐가 넘치면 OS 레벨에서 연결이 거부되는 것으로 추측.
- **fastapi-4w-async P99 19초**: async def에서 fib()를 직접 실행하면 이벤트 루프가 블로킹되어, 다른 요청들이 대기하면서 tail latency가 극단적으로 높아지는 것으로 추측.
- **Spring 메모리 사용량 높음**: JVM이 힙 메모리를 미리 할당하고, 클래스 로더/GC 메타데이터 등 런타임 오버헤드가 있기 때문으로 추측.

---

## 테스트 환경

| 항목 | 스펙 |
|---|---|
| Host | macOS (Apple Silicon) |
| Docker | CPU 4코어 / Memory 2GB 제한 |
| Python | 3.12 |
| Java | 21 (Eclipse Temurin) |
| Django | 4.x + Django Ninja + Gunicorn (sync / gevent / gthread) |
| FastAPI | + Uvicorn |
| Spring Boot | 3.4.4 + Tomcat |
| Load Test | k6 |

### 서버 구성 상세

| 구성 | 프레임워크 | 워커 모델 | 워커/스레드 수 |
|---|---|---|---|
| django-4w | Django + Gunicorn | sync | 워커 4 |
| django-16w | Django + Gunicorn | sync | 워커 16 |
| django-4w-gevent | Django + Gunicorn | gevent | 워커 4 (greenlet 다수) |
| django-4w-gthread | Django + Gunicorn | gthread | 워커 4 x 스레드 50 |
| fastapi-2w | FastAPI + Uvicorn | async | 워커 2 |
| fastapi-4w | FastAPI + Uvicorn | async | 워커 4 |
| fastapi-4w-async | FastAPI + Uvicorn | async (async def CPU) | 워커 4 |
| spring-default | Spring Boot + Tomcat | 스레드 풀 | 스레드 200 |
| spring-4t | Spring Boot + Tomcat | 스레드 풀 | 스레드 4 |
