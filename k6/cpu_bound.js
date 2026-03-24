import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const VUS = parseInt(__ENV.VUS || '100');
const RAMPUP = __ENV.RAMPUP || '10s';
const DURATION = __ENV.DURATION || '30s';

export const options = {
    scenarios: {
        default: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: RAMPUP, target: VUS },
                { duration: DURATION, target: VUS },
            ],
            gracefulStop: '0s',
            gracefulRampDown: '0s',
        },
    },
};

export default function () {
    const res = http.get(`${BASE_URL}/benchmark/cpu`);
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
    // no sleep — 최대 RPS 측정
}
