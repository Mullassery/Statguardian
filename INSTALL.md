# Installing StatGuard

## pip

```bash
pip install statguard
```

## uv

```bash
uv add statguard
```

## curl (one-liner, any Unix/macOS)

```bash
curl -sSfL https://raw.githubusercontent.com/Mullassery/statguard/main/install.sh | sh
```

## From source (Rust required)

```bash
# 1. Install Rust
curl -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# 2. Clone and build
git clone https://github.com/Mullassery/statguard.git
cd statguard
pip install maturin
maturin develop --release

# 3. Verify
python -c "import statguard; print(statguard.__version__)"
```

## Requirements

- Python ≥ 3.8
- `polars` ≥ 0.20 (installed automatically)
- Rust ≥ 1.75 (source builds only)

## Verify installation

```python
import statguard
print(statguard.__version__)

contract = statguard.DataContract.from_dsl("""
dataset test { schema { x: int, not_null } }
""")
import polars as pl
report = statguard.execute(contract, pl.DataFrame({"x": [1, 2, 3]}))
print(report.summary())
```
