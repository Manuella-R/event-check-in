"""Turns k6 CSV output into a before/after comparison chart.

1) Run each test with CSV output:
     k6 run --out csv=legacy.csv -e BASE_URL=http://<legacy-ip>:8000 scan.js
     k6 run --out csv=cloud.csv  -e BASE_URL=http://<alb-dns>       scan.js
2) Plot:
     pip install pandas matplotlib
     python plot_results.py "Legacy (1 server)=legacy.csv" "Cloud (autoscaling)=cloud.csv"
Output: results.png plus a summary table in the terminal.
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

WINDOW = 5  # seconds per data point


def load(path):
    parts = []
    # Read in chunks: k6 CSVs can have millions of rows.
    for chunk in pd.read_csv(path, usecols=["metric_name", "timestamp", "metric_value"], chunksize=500_000):
        parts.append(chunk[chunk.metric_name.isin(["http_req_duration", "http_req_failed"])])
    df = pd.concat(parts)
    df["t"] = ((df.timestamp - df.timestamp.min()) // WINDOW) * WINDOW
    dur = df[df.metric_name == "http_req_duration"]
    fail = df[df.metric_name == "http_req_failed"]
    return {
        "p95": dur.groupby("t").metric_value.quantile(0.95),                 # ms
        "rps": dur.groupby("t").metric_value.count() / WINDOW,               # requests/sec
        "err": fail.groupby("t").metric_value.mean() * 100,                  # % failed
        "all_p95": dur.metric_value.quantile(0.95),
        "all_rps": len(dur) / max(dur.timestamp.max() - dur.timestamp.min(), 1),
        "all_err": fail.metric_value.mean() * 100,
    }


runs = {}
for arg in sys.argv[1:]:
    label, path = arg.split("=", 1)
    runs[label] = load(path)
if not runs:
    sys.exit(__doc__)

fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
panels = [("p95", "p95 latency (ms)  - lower is better"),
          ("rps", "Throughput (requests/sec)"),
          ("err", "Error rate (%)  - lower is better")]
for ax, (key, title) in zip(axes, panels):
    for label, r in runs.items():
        ax.plot(r[key].index, r[key].values, label=label, linewidth=2)
    ax.set_title(title, loc="left", fontsize=11)
    ax.grid(alpha=0.3)
axes[0].legend()
axes[-1].set_xlabel("Seconds since test start")
fig.suptitle("Event check-in load test: legacy vs cloud", fontsize=14)
fig.tight_layout()
fig.savefig("results.png", dpi=150)

print(f"\n{'Setup':<28}{'p95 (ms)':>10}{'req/s':>10}{'errors %':>10}")
for label, r in runs.items():
    print(f"{label:<28}{r['all_p95']:>10.0f}{r['all_rps']:>10.1f}{r['all_err']:>10.2f}")
print("\nSaved results.png")
