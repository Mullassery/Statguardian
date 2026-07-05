# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

StatGuard is a Python library with a Rust engine. The codebase is a Cargo workspace with two layers:

1. **Rust core** (`crates/` directory):
   - `statguard-core`: AST and data contract parsing (pest parser for `.sg` files)
   - `statguard-engine`: Query execution planner and columnar operator pipeline
   - `statguard-validators`: Schema validation, quality rules, anomaly detection
   - `statguard-stats`: Statistical drift detection (percentile drift, distributional comparisons)
   - `statguard-io`: File/table format readers (Parquet, CSV, JSON, Avro, Delta, Iceberg)
   - `statguard-metrics`: Report generation and scoring
   - `statguard-py`: PyO3 FFI layer exposing Rust to Python

2. **Python layer**:
   - `python/statguard/` — minimal frontend wrapping the Rust binary via PyO3
   - Published to PyPI as `statguardian`

**Key design constraint**: Polars DataFrame passing across the PyO3 boundary requires matching build compatibility (`pyo3-polars` 0.18 / Polars 0.44). Users hitting `compat_level` errors should use `execute_file()` instead, which reads data on the Rust side.

## Build & Test Commands

**Build Rust**:
```bash
cd statguard
cargo build --release
cargo build --release --features extension-module  # For Python extension
```

**Run tests**:
```bash
cargo test --workspace                # All tests
cargo test -p statguard-core          # Single crate
cargo test --release --test "*"       # Integration tests
```

**Build Python wheel**:
```bash
maturin develop          # Dev install with hot reload
maturin build --release  # Build wheel for distribution
```

**Lint & format**:
```bash
cargo clippy --workspace --all-targets
cargo fmt --check
```

**Run examples**:
```bash
python examples/basic_validation.py
python examples/drift_detection.py
```

## Important Implementation Details

- **Contract parsing**: `.sg` files parsed via pest parser in `statguard-core`. Grammar is in `src/parser.rs`.
- **Execution model**: Lazy evaluation planner builds an operator DAG (Selection → Aggregation → Validation). No eager materialization until report generation.
- **Data format detection**: `statguard-io` sniffs file extensions and delegates to format-specific readers. Delta/Iceberg snapshots are time-travel capable.
- **Statistical drift**: Percentile drift computed as `|P_new - P_baseline| / |P_baseline|`. Configurable thresholds per metric.
- **Quality scoring**: Report `score` is 0-100 based on violations severity and count. Blocking violations = score 0.
