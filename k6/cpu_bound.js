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
