# Installing StatGuard

## Quick start (pip/uv)

### pip

```bash
pip install statguard
```

### uv (recommended)

```bash
uv add statguard
```

### curl (one-liner, any Unix/macOS)

```bash
curl -sSfL https://raw.githubusercontent.com/Mullassery/statguard/main/install.sh | sh
```

---

## Optional features

StatGuard ships with core features (DSL, schema validation, quality rules, drift detection).
Additional features require optional dependencies:

### Cloud storage (S3, GCS, Azure)

```bash
pip install statguard[cloud]
# Includes: AWS S3, Google Cloud Storage, Azure Blob Storage
```

Use with: `statguard.execute_cloud(contract, "s3://bucket/data/")`

### SQL databases

```bash
pip install statguard[sql]  # All SQL (Postgres, MySQL, SQLite, BigQuery, Snowflake, Redshift, Databricks, ClickHouse, DuckDB, Trino)
```

Or install per-database:

```bash
pip install statguard[sql-postgres]      # PostgreSQL (⚠️ adds LGPL-2.1 dependency)
pip install statguard[sql-mysql]         # MySQL / MariaDB
pip install statguard[sql-sqlite]        # SQLite
pip install statguard[sql-bigquery]      # Google BigQuery
pip install statguard[sql-snowflake]     # Snowflake
pip install statguard[sql-redshift]      # Amazon Redshift
pip install statguard[sql-databricks]    # Databricks
pip install statguard[sql-clickhouse]    # ClickHouse
pip install statguard[sql-duckdb]        # DuckDB
```

Use with: `statguard.execute_sql(contract, "postgresql://host/db", "SELECT * FROM table")`

### Apache Spark

```bash
pip install statguard[spark]
# Requires: PySpark 3.0+, PyArrow
```

Use with: `statguard.execute_spark(contract, spark_df)`

### Everything (all features)

```bash
pip install statguard[all]
```

---

## Requirements

### Base installation

- Python ≥ 3.8
- `polars` ≥ 0.20 (installed automatically)

### Optional dependencies

| Feature | Requirements |
|---------|--------------|
| Cloud (S3/GCS/Azure) | none (included with Polars) |
| PostgreSQL | psycopg2-binary ≥ 2.9 (⚠️ LGPL-2.1) |
| MySQL | pymysql ≥ 1.0 |
| SQLite | standard library |
| BigQuery | google-cloud-bigquery ≥ 3.0 |
| Snowflake | snowflake-connector-python ≥ 3.0 |
| Redshift | amazon-redshift-python-driver ≥ 1.0 |
| Databricks | databricks-sql-connector ≥ 1.0 |
| ClickHouse | clickhouse-driver ≥ 0.2 |
| DuckDB | duckdb ≥ 0.8 |
| Spark | pyspark ≥ 3.0, pyarrow ≥ 10 |

---

## From source (Rust required)

For development or building custom wheels:

```bash
# 1. Install Rust
curl -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# 2. Clone and install dependencies
git clone https://github.com/Mullassery/statguard.git
cd statguard
pip install maturin

# 3. Build with optional features
# Core only (default)
maturin develop --release

# With cloud storage
maturin develop --release --cargo-extra-args="--features cloud"

# With SQL (Postgres, MySQL, SQLite)
maturin develop --release --cargo-extra-args="--features sql"

# With everything
maturin develop --release --cargo-extra-args="--features full"

# 4. Verify
python -c "import statguard; print(statguard.__version__)"
```

### Rust requirements

- Rust ≥ 1.75 (run `rustup update` to upgrade)
- `maturin` ≥ 1.7 (`pip install maturin`)

---

## Verify installation

### Python API

```python
import statguard

# Check version
print(statguard.__version__)

# Basic validation
contract = statguard.DataContract.from_dsl("""
dataset test {
    schema { x: int, not_null }
    quality { completeness(x) > 0.9 }
}
""")

import polars as pl
df = pl.DataFrame({"x": [1, 2, None, 4]})
report = statguard.execute(contract, df)
print(report.summary())
# Output: [StatGuard] PASS ✓ | dataset=test | score=0.95 (A) | rows=4 | violations=0 | 1ms
```

### CLI

```bash
# Create a test contract
cat > test.sg << 'EOF'
dataset test { schema { x: int, not_null } }
EOF

# Create test data
python3 -c "
import polars as pl
pl.DataFrame({'x': [1, 2, 3]}).write_parquet('test.parquet')
"

# Validate
statguard validate --contract test.sg --file test.parquet
# Output: [StatGuard] PASS ✓ | dataset=test | score=1.0 (A) | rows=3 | violations=0 | 1ms
```

### Test cloud (requires AWS credentials)

```bash
pip install statguard[cloud]

python3 << 'EOF'
import statguard
contract = statguard.DataContract.from_dsl("dataset test { schema { x: int } }")

# This requires AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY in env
try:
    report = statguard.execute_cloud(contract, "s3://my-bucket/test.parquet")
    print(report.summary())
except Exception as e:
    print(f"Cloud test (expected if S3 access not configured): {e}")
EOF
```

---

## Troubleshooting

### `ImportError: No module named 'statguard'`

StatGuard is not installed. Install it:

```bash
pip install statguard
```

### `ImportError: cannot import name 'execute_cloud'` (cloud not installed)

Cloud storage feature not installed. Install it:

```bash
pip install statguard[cloud]
```

### `ImportError: cannot import name 'execute_sql'` (SQL not installed)

SQL feature not installed. Install it:

```bash
pip install statguard[sql]
```

### `psycopg2 ImportError` (PostgreSQL not installed)

PostgreSQL driver not installed. Install it:

```bash
pip install statguard[sql-postgres]
```

Note: This adds `psycopg2-binary` (LGPL-2.1 license). See [LICENSES.md](../LICENSES.md) for compliance details.

### Build error on macOS/Linux (from source)

Ensure Rust is installed and up-to-date:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
rustup update
```

Then rebuild:

```bash
maturin develop --release
```

### Polars version conflict

StatGuard requires Polars ≥ 0.20. Upgrade it:

```bash
pip install --upgrade polars
```

---

## Next steps

- **Quick start**: See [README.md](../README.md)
- **DSL guide**: See [README.md#dsl-reference](../README.md#dsl-reference)
- **CLI reference**: See [docs/CLI.md](CLI.md)
- **Format compatibility**: See [docs/FORMAT_COMPATIBILITY.md](FORMAT_COMPATIBILITY.md)
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)
