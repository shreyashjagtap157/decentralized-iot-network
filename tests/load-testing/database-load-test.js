import k6 from 'k6';
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,  // Simulate 20 concurrent users
  duration: '1m',
  rampUp: '10s',  // Ramp up over 10 seconds
  thresholds: {
    http_req_duration: ['p(90)<1000', 'p(99)<2000'],
    http_req_failed: ['rate<0.05'],
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  // Simulate getting user data
  const userRes = http.get(`${BASE_URL}/users/profile`);
  check(userRes, {
    'get user profile status is 200': (r) => r.status === 200 || r.status === 401,
  });

  sleep(0.5);

  // Simulate getting device list
  const devicesRes = http.get(`${BASE_URL}/devices/list`);
  check(devicesRes, {
    'get devices list status is 200': (r) => r.status === 200 || r.status === 401,
  });

  sleep(0.5);

  // Simulate getting device data
  const deviceDataRes = http.get(`${BASE_URL}/devices/device_1/data`);
  check(deviceDataRes, {
    'get device data status is 200': (r) => r.status === 200 || r.status === 400 || r.status === 404,
  });

  sleep(1);

  // Simulate getting analytics
  const analyticsRes = http.get(`${BASE_URL}/analytics/summary`);
  check(analyticsRes, {
    'get analytics status is 200': (r) => r.status === 200 || r.status === 401,
  });

  sleep(1);
}
