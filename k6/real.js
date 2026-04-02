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
    // 복합 필터 + 정렬 쿼리
    const minEnergy = Math.floor(Math.random() * 200);          // 0~199
    const maxEnergy = minEnergy + 80 + Math.floor(Math.random() * 150);   // min+80 ~ min+229

    const sortFields = ['food_name', 'energy_kcal', 'protein_g', 'fat_g', 'carbohydrate_g'];
    const sort = sortFields[Math.floor(Math.random() * sortFields.length)];

    const page = Math.floor(Math.random() * 10) + 1;

    const url = `${BASE_URL}/api/foods/search?min_energy=${minEnergy}&max_energy=${maxEnergy}&sort=${sort}&page=${page}&size=20`;
    const res = http.get(url, { tags: { name: 'foods_search' } });
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
}
