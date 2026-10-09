# Step-by-step guide (Windows, PowerShell)

Total time: about 5 to 7 days at a relaxed pace. Each phase ends with something you can screenshot or put on your CV.
All commands run from the project folder unless stated otherwise.

## Folder map
```
check_in\
  app\                      Flask API, Dockerfile, seed script
  tests\                    unit tests + concurrency test
  loadtest\                 k6 script + graph script
  nginx\  monitoring\       load balancer + Prometheus/Grafana config
  terraform\                AWS design (not deployed)
  docs\                     cost estimate template
  .github\workflows\ci.yml  CI/CD pipeline
  docker-compose.yml        single-server ("legacy") stack
  docker-compose.scaled.yml load-balanced + monitored stack
  run_test.ps1              one test against any URL
  run_scaled.ps1            1-vs-4 replicas comparison
```

---
## Step 0: Set up the new folder (15 min)
1. Unzip `checkin-app-v2.zip` to `C:\projects\check_in_v2` (not OneDrive).
2. Stop anything running from before:
   ```powershell
   cd C:\projects\check_in      # your old folder
   docker compose down -v
   ```
3. Install Python packages (once):
   ```powershell
   cd C:\projects\check_in_v2
   pip install -r app\requirements.txt -r app\requirements-dev.txt pandas matplotlib
   ```
4. Check Docker Desktop is running (green "Engine running").

---
## Phase 1: Verify the app works (1 to 2 hours)
**1.1 Run the unit tests**
```powershell
pytest -q
```
Expect `6 passed, 1 skipped` (the concurrency test is skipped because no database is configured).

**1.2 Start the single-server stack and seed it**
```powershell
docker compose up -d --build
docker compose exec app python seed.py 10000
Invoke-RestMethod http://localhost:8000/stats
```
**1.3 Run the concurrency test against the real database**
```powershell
$env:DB_HOST="localhost"; $env:DB_POOL_MAX="10"
pytest -v
Remove-Item Env:DB_HOST
```
Expect `7 passed`. This proves exactly one of 100 simultaneous scans of one ticket is admitted. Screenshot it.

**1.4 Smoke-test the load script, then shut down**
```powershell
.\run_test.ps1 -Name smoke -Quick -ResetLocalDb
docker compose down -v
```
Delete `results\smoke.csv` afterwards.

---
## Phase 2: Scale it, the headline result (half a day)
**2.1 Start the scaled stack and seed it**
```powershell
docker compose -f docker-compose.scaled.yml up -d --build
docker compose -f docker-compose.scaled.yml exec app python seed.py 10000
Invoke-RestMethod http://localhost:8080/stats
```
**2.2 Close heavy apps** (browser tabs, games). The load generator shares your laptop with the app.

**2.3 Run the comparison** (about 10 minutes: two 4-minute tests)
```powershell
powershell -ExecutionPolicy Bypass -File .\run_scaled.ps1 -Peak 200
```
It runs the same test with 1 replica and then 4, resets the tickets before each run, and writes `results\scaling.png` plus a summary table.

**2.4 Record the numbers** (p95, req/s, error %) in the README results table. If 4 replicas are not clearly better, that is a finding: look at Grafana (Phase 3) for the bottleneck (usually the database or the laptop CPU). Try `-Peak 300` or a different replica set like `-Replicas 1,2,4`.

---
## Phase 3: Monitoring (half a day)
The scaled stack already runs Prometheus and Grafana.
1. Grafana: http://localhost:3000 > Dashboards > **Check-in overview**.
2. Prometheus alerts: http://localhost:9090/alerts
3. Start a test and watch the dashboard react:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_scaled.ps1 -Peak 300 -Replicas 1
   ```
4. **Screenshots to take** (save in `docs\images\`): `grafana.png` (dashboard during the peak) and `alert.png` (an alert in **Firing** state; a 1-replica run at high peak should trigger `HighP95Latency`).
5. Check the raw metrics: `Invoke-RestMethod http://localhost:8080/metrics`.

---
## Phase 4: CI/CD (half a day)
**4.1 Safety check before anything goes public**
```powershell
git init
git add .
git status
```
Make sure no `.pem`, `.sql`, `.env`, or `results\*.csv` files are listed.

**4.2 Create the repo.** On github.com: New repository, name it e.g. `event-checkin-scaling`, **do not** add a README. Then:
```powershell
git branch -M main
git commit -m "Event check-in: scaling, monitoring, CI/CD, AWS design"
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```
**4.3 Watch the pipeline:** repo > Actions tab. Jobs: `test` (unit + concurrency against a Postgres container), then `build-and-push`. Both should go green.

**4.4 Make the image public:** your profile > Packages > the image > Package settings > Change visibility > Public (needed if Render pulls it).

**4.5 Add the badge:** in `README.md` replace `YOUR-USER/YOUR-REPO` with your values.

**4.6 Optional: deploy to Render for a public demo URL.** Render > New > Web Service > Existing image > `ghcr.io/<your-user>/<your-repo>:latest`. Add env vars `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE=require` from a Render Postgres. Seed it from your laptop (set the same env vars, then `python app\seed.py 10000`). To redeploy automatically, copy the service's **Deploy Hook** URL into GitHub: repo > Settings > Secrets and variables > Actions > `RENDER_DEPLOY_HOOK_URL`. Free instances sleep and are slow, so use it as a demo link, not for benchmarking.

---
## Phase 5: Design the AWS version without an account (1 to 2 days)
**5.1 Terraform check**
```powershell
winget install Hashicorp.Terraform
# restart PowerShell, then:
cd terraform
terraform init -backend=false
terraform fmt
terraform validate
cd ..
```
Expect `Success! The configuration is valid.` I could not run Terraform where I built this, so if `validate` reports an error, paste it to me and I will fix it. Do not run `terraform apply` (it needs an AWS account and costs money).

**5.2 Cost estimate.** Open https://calculator.aws (no account needed), build the Scenario A and B estimates from `docs\aws-cost-estimate.md`, screenshot them into `docs\images\`, and fill the tables. Write the honest conclusion.

**5.3 Diagrams.** Already in `README.md` as Mermaid (GitHub renders them). Check them on GitHub after pushing.

---
## Phase 6: Package for your CV (half a day)
1. Fill every `[X]`, `[Y]`, `[PEAK]` in `README.md` with **measured** numbers, and write the "What I found" paragraph honestly.
2. Copy `results\scaling.png` into the repo (it is not ignored; the CSVs are).
3. Push the final version: `git add . ; git commit -m "Add results and screenshots" ; git push`.
4. Pin the repo on your GitHub profile. Add the link to your CV and LinkedIn.
5. CV entry (use only numbers you measured):
   > **Event Check-in System: Scalable Architecture** | Python, Flask, PostgreSQL, Docker, nginx, k6, Prometheus, Grafana, GitHub Actions, Terraform
   > - Built a check-in API with an atomic database update, verified by a concurrency test (100 simultaneous scans, exactly one admitted)
   > - Load tested with k6 and cut p95 latency from **[X] ms to [Y] ms** by moving to a load-balanced, multi-replica setup
   > - Added Prometheus/Grafana dashboards and alert rules, and automated tests and image builds with GitHub Actions
   > - Designed the AWS equivalent (ALB, ECS Fargate, RDS, autoscaling) in Terraform with a cost estimate and migration plan

---
## Troubleshooting
| Problem | Fix |
|---|---|
| `docker compose` build fails on a missing path | Run from the folder that contains `app\` and the compose file |
| `run_scaled.ps1` says "Database not seeded" | Run the seed command from step 2.1 |
| Grafana panels show "No data" | Run a test first; wait about 15 seconds; check http://localhost:9090/targets shows replicas UP |
| Prometheus targets list only 1 replica | Make sure `run_scaled.ps1` finished scaling, or `docker compose -f docker-compose.scaled.yml ps` |
| k6 shows high errors at peak locally | Lower `-Peak`; the laptop is the bottleneck. Say so in the README |
| Port already in use (8000, 8080, 3000, 9090) | `docker ps`, stop old containers with `docker compose down` |
| CI `test` job fails on the DB | Re-run the job; Postgres container may have started slowly |
| `git push` rejected or asks for login | Use a GitHub personal access token or GitHub Desktop sign-in |

## Label everything honestly
| Item | Say |
|---|---|
| Single-server baseline, nginx replicas, monitoring | "Deployed locally (Docker Compose)" |
| CI/CD pipeline | "Running on GitHub Actions" |
| AWS architecture | "Designed in Terraform and validated; not deployed" |
Never describe the nginx setup as autoscaling or as running on AWS.
