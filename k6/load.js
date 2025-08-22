import http from 'k6/http';
import { sleep, check } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 50 },
    { duration: '8m', target: 50 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const GATEWAY = __ENV.GATEWAY_BASE;
const API_KEY = __ENV.API_TOKEN || '';

export default function () {
  let headers = { 'x-api-key': API_KEY, 'content-type': 'application/json' };
  let r1 = http.get(`${GATEWAY}/health`, { headers });
  check(r1, { 'health ok': (r) => r.status === 200 });

  // Write (idempotent) to a mock capability endpoint (adjust path in env if needed)
  const key = `k6-${__ITER}`;
  let r2 = http.post(`${GATEWAY}/proxy/integrations/capability/smartthings/abc/switch/on`, '{}', { headers: { ...headers, 'Idempotency-Key': key } });
  check(r2, { 'switch ok or accepted': (r) => r.status < 500 });

  sleep(1);
}