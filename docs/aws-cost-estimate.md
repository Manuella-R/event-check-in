# AWS cost estimate (from the AWS Pricing Calculator)

Calculator: https://calculator.aws  (no AWS account needed). Region: eu-west-1.
Fill the right-hand column from the calculator; keep a screenshot in `docs/images/`.

## Scenario A: event weekend (resources run 3 days)
| Service | Configuration | Monthly price shown | Prorated for 3 days |
|---|---|---|---|
| ECS Fargate | 2 to 6 tasks, 0.5 vCPU / 1 GB | | |
| Application Load Balancer | 1 ALB, low traffic | | |
| RDS PostgreSQL | db.t4g.micro, single-AZ, 20 GB | | |
| CloudWatch Logs | ~1 GB | | |
| **Total** | | | |

## Scenario B: always-on for a year (compare with a server sized for peak)
| Option | Cost per year |
|---|---|
| Always-on cloud stack | |
| Single on-prem / VPS server sized for peak | |

## Conclusion
Write 2 to 3 honest sentences. Real peak load for 10k attendees is only tens of
scans per second, so cloud wins mainly on availability, burst handling and
pay-per-use, not raw speed.
