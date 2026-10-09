// Simulates check-in stations scanning tickets. Run the SAME script for every setup.
//   k6 run -e BASE_URL=http://localhost:8080 -e PEAK=200 loadtest/scan.js
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const PEAK = Number(__ENV.PEAK || 500);   // peak virtual users
const TICKETS = 10000;

export const options = {
  stages: [
    { duration: '30s', target: Math.round(PEAK * 0.1) },  // doors opening
    { duration: '1m',  target: Math.round(PEAK * 0.4) },  // building up
    { duration: '2m',  target: PEAK },                    // peak rush
    { duration: '30s', target: 0 },                       // quiet again
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

// 200 admitted, 404 invalid, 409 already-used are normal business outcomes.
http.setResponseCallback(http.expectedStatuses(200, 404, 409));

export default function () {
  const ticket = 'T' + String(Math.floor(Math.random() * TICKETS) + 1).padStart(5, '0');
  const station = (__VU % 6) + 1;
  const res = http.post(
    `${BASE_URL}/scan`,
    JSON.stringify({ ticket_id: ticket, station_id: station }),
    { headers: { 'Content-Type': 'application/json' } },
  );
  check(res, { 'no server error': (r) => r.status < 500 });
}
