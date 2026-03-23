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
