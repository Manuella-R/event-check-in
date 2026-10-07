# Event check-in: legacy setup

## Run locally
    docker compose up -d --build
    docker compose exec app python seed.py 10000
    curl -X POST localhost:8000/scan -H 'Content-Type: application/json' \
         -d '{"ticket_id":"T00001","station_id":1}'
    curl localhost:8000/stats

## Load test
    k6 run -e BASE_URL=http://localhost:8000 loadtest/scan.js
