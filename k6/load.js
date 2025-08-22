import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  vus: 20,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const GATEWAY = __ENV.GATEWAY_BASE;
const API_KEY = __ENV.API_TOKEN || '';

export default function () {
  let headers = { 'x-api-key': API_KEY };
  let res1 = http.get(`${GATEWAY}/health`, { headers });
  check(res1, { 'health ok': (r) => r.status === 200 });

  const target = encodeURIComponent(`${GATEWAY}/openapi/v1.json`);
  let res2 = http.get(`${GATEWAY}/proxy?url=${target}`, { headers });
  check(res2, { 'proxy ok': (r) => r.status === 200 });

  sleep(1);
}