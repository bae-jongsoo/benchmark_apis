# 05. k6 부하 테스트 스크립트

## 목표
k6 테스트 스크립트 5개를 작성한다. Phase 1(CPU Bound, IO Bound, Mixed)과 Phase 2(Real Simple, Real Heavy) 시나리오 각각에 대응한다.

## 선행 태스크
- 01-project-setup (config.yaml — 테스트 파라미터 참조)
- 02-django-app, 03-fastapi-app (엔드포인트 경로 확인)

## 공통 사항

### 테스트 파라미터 (config.yaml 기본값 기준)
| 항목 | 값 |
|------|------|
| 테스트 시간 | 40초 |
| 동시 사용자 수 (VUs) | 100 |
| Ramp-up | 10초간 0→100 VUs |
| 대기 시간 | 0 (no wait) — 최대 RPS 측정 |

### k6 stages 설정
```javascript
export const options = {
    stages: [
        { duration: '10s', target: 100 },   // ramp-up: 0→100 VUs (10초)
        { duration: '30s', target: 100 },   // sustained: 100 VUs 유지 (30초)
    ],
    // 대기 시간 없음 — VU가 응답 받으면 즉시 다음 요청
};
```

### 환경변수
k6 스크립트는 `__ENV.BASE_URL` 환경변수로 대상 서버 URL을 받는다.
`run_benchmark.py`에서 구성별로 URL을 주입한다.

```javascript
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
```

### 출력
k6 JSON 출력: `--out json=results/<phase>/raw/<scenario>_<config>.json`
- `run_benchmark.py`에서 출력 경로를 지정한다

## 구현할 파일 목록

### 1. `k6/cpu_bound.js` — Phase 1: CPU Bound

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 100 },
    ],
};

export default function () {
    const res = http.get(`${BASE_URL}/benchmark/cpu`);
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
    // no sleep — 최대 RPS 측정
}
```

### 2. `k6/io_bound.js` — Phase 1: IO Bound

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 100 },
    ],
};

export default function () {
    const res = http.get(`${BASE_URL}/benchmark/io`);
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
}
```

### 3. `k6/mixed.js` — Phase 1: Mixed

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 100 },
    ],
};

export default function () {
    const res = http.get(`${BASE_URL}/benchmark/mixed`);
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
}
```

### 4. `k6/real_simple.js` — Phase 2: Real Simple (단순 페이지네이션)

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 100 },
    ],
};

export default function () {
    // 랜덤 페이지 조회 (1~100 페이지 중 랜덤)
    const page = Math.floor(Math.random() * 100) + 1;
    const res = http.get(`${BASE_URL}/api/foods?page=${page}&size=20`);
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
}
```

### 5. `k6/real_heavy.js` — Phase 2: Real Heavy (복합 쿼리)

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '30s', target: 100 },
    ],
};

export default function () {
    // 복합 필터 + 정렬 쿼리
    const minEnergy = Math.floor(Math.random() * 200);          // 0~199
    const maxEnergy = minEnergy + 100 + Math.floor(Math.random() * 400);  // min+100 ~ min+499

    const sortFields = ['food_name', 'energy_kcal', 'protein_g', 'fat_g', 'carbohydrate_g'];
    const sort = sortFields[Math.floor(Math.random() * sortFields.length)];

    const page = Math.floor(Math.random() * 10) + 1;

    const url = `${BASE_URL}/api/foods/search?min_energy=${minEnergy}&max_energy=${maxEnergy}&sort=${sort}&page=${page}&size=20`;
    const res = http.get(url);
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
}
```

**주요 포인트**:
- Real Heavy에서 `data_type` 필터는 선택적으로 포함할 수 있으나, 기본적으로 에너지 범위 + 정렬 필터로 충분한 복합 쿼리를 생성한다
- 랜덤 파라미터를 사용하여 캐시 효과를 줄인다

## k6 실행 방법 (참고 — run_benchmark.py에서 자동 실행)

```bash
# Docker 컨테이너로 실행 (docker-compose.yml의 k6 서비스)
docker compose run --rm \
  -e BASE_URL=http://host.docker.internal:8001 \
  k6 run \
  --out json=/results/phase1/raw/cpu_bound_django-4w.json \
  /scripts/cpu_bound.js
```

## 완료 기준
- `k6/` 디렉토리에 5개 스크립트가 존재한다:
  - `cpu_bound.js`, `io_bound.js`, `mixed.js`, `real_simple.js`, `real_heavy.js`
- 모든 스크립트가 `BASE_URL` 환경변수를 통해 대상 서버를 지정할 수 있다
- stages 설정이 기획서의 테스트 파라미터(ramp-up 10초, sustained 30초)와 일치한다
- 대기 시간 없이 최대 RPS를 측정한다
- 각 요청에 대해 HTTP 200 check를 수행한다
