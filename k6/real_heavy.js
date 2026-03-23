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
