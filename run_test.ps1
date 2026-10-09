<#
 One command: (optionally reset the DB) -> run k6 -> save CSV -> draw comparison graph.

 Examples (run from the project folder):
   .\run_test.ps1 -Name local-test -Quick -ResetLocalDb      # fast smoke test on your laptop
   .\run_test.ps1 -Name legacy -BaseUrl http://<ec2-ip>:8000  # real "before" run
   .\run_test.ps1 -Name cloud  -BaseUrl http://<alb-dns>      # real "after" run

 The graph (results\results.png) overlays EVERY csv in the results folder,
 so after the legacy and cloud runs you get the before/after comparison.
#>
param(
  [string]$Name = "legacy",
  [string]$BaseUrl = "http://localhost:8000",
  [switch]$ResetLocalDb,   # only for the local docker-compose database
  [switch]$Quick           # 50 users for 30s instead of the full 4-minute ramp to 500
)

Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force results | Out-Null

if ($ResetLocalDb) {
  Write-Host "Resetting tickets so the run starts fresh..."
  docker compose exec -T db psql -U checkin -d checkin -c "UPDATE tickets SET checked_in=FALSE, checked_in_at=NULL, station_id=NULL;"
}

$csv = "results\$Name.csv"
$k6args = @("run", "--out", "csv=$csv", "-e", "BASE_URL=$BaseUrl")
if ($Quick) { $k6args += @("--vus", "50", "--duration", "30s") }
$k6args += "loadtest\scan.js"

Write-Host "Running k6 against $BaseUrl ..."
k6 @k6args   # a failed threshold makes k6 exit non-zero; we still want the graph

$plotArgs = Get-ChildItem results\*.csv | ForEach-Object { "$($_.BaseName)=$($_.Name)" }
Push-Location results
python ..\loadtest\plot_results.py @plotArgs
Pop-Location

Write-Host "`nDone. Open results\results.png"
