import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',

  summaryTrendStats: [
    'avg',
    'med',
    'p(95)',
    'p(99)',
    'max',
  ],
};

export default function () {
  const res = http.get(
    'http://host.docker.internal:30080/api/riesgo/Casablanca'
  );

  check(res, {
    'status 200': (r) => r.status === 200,
  });

  sleep(1);
}