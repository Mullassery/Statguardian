# StatGuard

**High-performance Data Quality, Validation & Statistical Drift Monitoring Engine**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/statguard)](https://pypi.org/project/statguard)

StatGuard is a **Rust-native** data contract system. You define a single declarative contract — schema rules, business constraints, statistical expectations — and StatGuard compiles it into an optimised execution DAG that runs 10–50× faster than Python-based alternatives.

---

## Features

| Capability | Details |
|---|---|
| **Schema validation** | types, nullability, uniqueness, regex, ranges, enums |
| **Quality rules** | completeness, uniqueness, validity — with severity levels |
| **Statistical drift** | PSI, KS-test, mean/std/percentile drift with configurable thresholds |
| **Anomaly detection** | IQR & z-score outliers, duplicate detection, cardinality explosion |
| **Batch & streaming** | same contract, same API — file-at-once or micro-batch window |
| **Profiling** | min/max/mean/std/percentiles/histogram + HyperLogLog cardinality |
| **Observability** | Prometheus text format, structured JSON reports, health scores |
| **Python API** | native Polars DataFrames in, typed Python objects out |

---

## Install

```bash
# pip
pip install statguard

# uv (recommended)
uv add statguard

# from source (requires Rust + maturin)
curl -sSf https://sh.rustup.rs | sh
pip install maturin
maturin develop --release
```

---

## Quick Start

### Python

```python
import polars as pl
import statguard

# 1. Define a data contract
contract = statguard.DataContract.from_dsl("""
dataset users {
    schema {
        id:      int,    not_null, unique
        email:   string, regex="^[^@]+@[^@]+\\.[^@]+$"
        age:     int,    between(0, 120)
        country: string, not_null
        score:   float,  min=0.0, max=1.0
    }
    quality {
        completeness(id)    > 0.99
        @warning: uniqueness(email) == 1.0
    }
    stats {
        age.mean drift < 0.10
        age.std  drift < 0.20
    }
    anomalies {
        detect_outliers(age, method="iqr")
        @blocking: detect_duplicates(id)
    }
}
""")

# 2. Load data (any Polars-supported format)
df = pl.read_csv("users.csv")

# 3. Execute
report = statguard.execute(contract, df)

print(report.summary())
# [StatGuard] PASS ✓ | dataset=users | score=0.97 (A) | rows=50000 | violations=2 ...

# 4. Structured output
for v in report.violations():
    print(v["column"], v["severity"], v["message"])

# 5. Drift detection (provide a reference / yesterday's data)
ref = pl.read_parquet("users_yesterday.parquet")
report_with_drift = statguard.execute(contract, df, reference=ref)
for d in report_with_drift.drift_results():
    print(d["column"], d["stat"], f"drift={d['drift']:.4f}")
```

### CLI

```bash
# Validate a file
statguard validate --contract users.sg --file users.parquet

# With drift reference
statguard validate --contract users.sg --file today.parquet --reference yesterday.parquet

# Prometheus output (for scraping)
statguard validate --contract users.sg --file data.parquet --format prometheus

# Syntax-check DSL only
statguard check --contract users.sg

# Fail CI on any violation
statguard validate --contract users.sg --file data.parquet --fail-on-warning && echo "OK"
```

### Streaming

```python
# Process a large file in 10 000-row batches
reports = statguard.execute_streaming(contract, "huge_file.parquet", batch_size=10_000)
for i, r in enumerate(reports):
    print(f"Batch {i}: {r.summary()}")
```

---

## DSL Reference

```
dataset <name> {
    schema {
        <field>: <type>[, <constraint>]*
    }
    quality {
        [<severity>:] <metric>(<field>) <op> <value>
    }
    stats {
        [<severity>:] <field>.<stat> drift <op> <value>
    }
    anomalies {
        [<severity>:] <function>(<field>[, <arg>=<value>]*)
    }
    stream {           // optional streaming config
        window    = "5m"
        watermark = "30s"
        emit      = "on_window_close"
    }
}
```

**Types:** `int` · `float` · `string` · `bool` · `date` · `datetime` · `bytes`

**Constraints:** `not_null` · `unique` · `primary_key` · `positive` · `negative` · `coerce` · `regex="..."` · `between(lo, hi)` · `min=N` · `max=N` · `len(min, max)` · `enum=["a","b"]`

**Quality metrics:** `completeness` · `uniqueness` · `validity` · `consistency` · `non_null_rate`

**Stat functions (drift):** `mean` · `std` · `median` · `min` · `max` · `p05` · `p95` · `p99` · `p999`

**Anomaly functions:** `detect_outliers(method="iqr"|"zscore")` · `detect_duplicates` · `detect_nulls` · `detect_cardinality_explosion`

**Severity prefixes:** `@info:` · `@warning:` · `@error:` (default) · `@blocking:`

---

## Architecture

```
statguard/
├── crates/
│   ├── statguard-core/         DSL parser (pest PEG), AST, compiler, DAG, optimizer
│   ├── statguard-engine/       Execution engine — batch + streaming (Polars + Rayon)
│   ├── statguard-validators/   Schema validator, rule engine
│   ├── statguard-stats/        Profiler, drift detection (PSI, KS), HyperLogLog
│   ├── statguard-io/           Parquet/CSV/JSON/IPC reader, streaming batcher
│   ├── statguard-metrics/      Report generation, health scores, Prometheus output
│   └── statguard-py/           PyO3 Python bindings
└── python/
    └── statguard/              Pure-Python shim + CLI
```

### Compilation pipeline

```
DSL text
   │
   ▼ pest PEG parser
AST (DataContract)
   │
   ▼ Compiler
Raw DAG nodes
   │
   ▼ Optimizer (deduplicate → fuse null checks → sort by cost)
ExecutionDag (ordered, column-grouped)
   │
   ▼ BatchExecutor (Rayon parallel per column)
ValidationReport (violations + drift + profiles + health score)
```

### Performance

- **Zero row loops** — all operations are columnar (Polars/Arrow-backed)
- **Parallel by column** — Rayon distributes column checks across cores
- **Cost-ordered checks** — cheap checks (type, null) run before expensive ones (regex, uniqueness), enabling early exit
- **HyperLogLog** — O(1) memory cardinality estimation at 0.81% error rate

---

## Report output

```json
{
  "id": "a1b2c3...",
  "dataset": "users",
  "passed": true,
  "health": { "score": 0.972, "grade": "A", "drift_score": 1.0 },
  "violations": [
    { "column": "age", "check": "between", "severity": "Error", "message": "3 values out of range [0, 120]" }
  ],
  "drift_results": [
    { "column": "age", "stat": "mean", "drift": 0.032, "psi": 0.004, "passed": true }
  ],
  "column_profiles": [
    { "name": "age", "mean": 34.2, "std": 12.1, "null_rate": 0.001, "distinct_count": 98 }
  ]
}
```

---

## License

MIT © 2026 [Georgi Mammen Mullassery](https://github.com/Mullassery)
