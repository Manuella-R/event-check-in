// Simulates check-in stations scanning tickets. Run the SAME script against
// legacy and cloud so the before/after comparison is fair.
//   k6 run -e BASE_URL=http://<host>:8000 loadtest/scan.js
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TICKETS = 10000;

export const options = {
  stages: [
    { duration: '30s', target: 50 },    // doors opening
    { duration: '1m',  target: 200 },   // building up
    { duration: '2m',  target: 500 },   // peak rush
    { duration: '30s', target: 0 },     // quiet again
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // pass/fail: 95% of scans under 500 ms
    http_req_failed: ['rate<0.01'],     // under 1% errors
  },
};

// 200 admitted, 404 invalid and 409 already-used are all valid business outcomes,
// so they shouldn't count as failures. Only 5xx and timeouts should.
http.setResponseCallback(http.expectedStatuses(200, 404, 409));

export default function () {
  const ticket = 'T' + String(Math.floor(Math.random() * TICKETS) + 1).padStart(5, '0');
  const station = (__VU % 6) + 1;   // spreads virtual users across 6 stations

  const res = http.post(
    `${BASE_URL}/scan`,
    JSON.stringify({ ticket_id: ticket, station_id: station }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, { 'no server error': (r) => r.status < 500 });
}
