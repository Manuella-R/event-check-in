<#
 Runs the SAME load test against the scaled stack with different replica counts,
 then draws one comparison graph (results\scaling.png).

   .\run_scaled.ps1                       # 1 replica vs 4 replicas, peak 200 users
   .\run_scaled.ps1 -Peak 300 -Replicas 1,2,4

 Prerequisite: the scaled stack is up and seeded (see GUIDE.md, Phase 2).
#>
param(
  [int]$Peak = 200,
  [int[]]$Replicas = @(1, 4)
)

Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force results | Out-Null
$compose = @("compose", "-f", "docker-compose.scaled.yml")
$base = "http://localhost:8080"
$plotArgs = @()

foreach ($n in $Replicas) {
  Write-Host "`n=== $n replica(s) ===" -ForegroundColor Cyan
  docker @compose up -d --scale "app=$n" | Out-Null
  docker @compose restart nginx | Out-Null   # nginx re-resolves the replica list on restart

  $ready = $false
  for ($i = 0; $i -lt 30 -and -not $ready; $i++) {
    try { Invoke-RestMethod "$base/health" | Out-Null; $ready = $true } catch { Start-Sleep -Seconds 2 }
  }
  if (-not $ready) { throw "Stack did not become healthy. Run: docker compose -f docker-compose.scaled.yml logs" }

  try { $s = Invoke-RestMethod "$base/stats" } catch { throw "Database not seeded. Run: docker compose -f docker-compose.scaled.yml exec app python seed.py 10000" }
  if ($s.total -eq 0) { throw "No tickets found. Seed the database first (see GUIDE.md)." }

  docker @compose exec -T db psql -U checkin -d checkin -c "UPDATE tickets SET checked_in=FALSE, checked_in_at=NULL, station_id=NULL;" | Out-Null

  $csv = "results\replicas-$n.csv"
  k6 run --out "csv=$csv" -e "BASE_URL=$base" -e "PEAK=$Peak" loadtest\scan.js
  $plotArgs += "$n replica(s)=replicas-$n.csv"
}

Push-Location results
$env:PLOT_OUT = "scaling.png"
python ..\loadtest\plot_results.py @plotArgs
Pop-Location
Write-Host "`nDone. Open results\scaling.png" -ForegroundColor Green
