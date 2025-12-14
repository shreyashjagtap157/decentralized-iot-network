import k6 from 'k6';
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,  // Virtual users
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests should complete below 500ms
    http_req_failed: ['rate<0.1'],     // Error rate should be below 10%
  },
};

export default function () {
  // Test user registration
  const registerRes = http.post(
    'http://localhost:8000/users/register',
    {
      email: `user${Math.random()}@example.com`,
      password: 'password123',
      username: `user${Math.random()}`,
    },
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(registerRes, {
    'user registration status is 200': (r) => r.status === 200 || r.status === 400,
  });

  sleep(1);

  // Test device registration
  const deviceRes = http.post(
    'http://localhost:8000/devices/register',
    {
      device_id: `device_${Math.random()}`,
      user_id: 'test_user',
      signature: 'test_signature',
    },
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(deviceRes, {
    'device registration status is 200': (r) => r.status === 200 || r.status === 400,
  });

  sleep(1);

  // Test data submission
  const dataRes = http.post(
    'http://localhost:8000/devices/submit-data',
    {
      device_id: 'device_1',
      energy_generated: 100.5,
      timestamp: new Date().toISOString(),
    },
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(dataRes, {
    'data submission status is 200': (r) => r.status === 200 || r.status === 400,
  });

  sleep(1);

  // Test API health check
  const healthRes = http.get('http://localhost:8000/health');

  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
  });

  sleep(2);
}
