.PHONY: install install-dev build test lint fmt clean help setup-hooks

help:
	@echo "statguard development tasks:"
	@echo "  make install         Install pre-commit hooks"
	@echo "  make build           Build release binary"
	@echo "  make test            Run all tests"
	@echo "  make test-unit       Run unit tests only"
	@echo "  make lint            Run clippy linter"
	@echo "  make fmt             Format code"
	@echo "  make fmt-check       Check format without changing"
	@echo "  make clean           Remove build artifacts"

install: setup-hooks
	@echo "✓ Development environment ready"

setup-hooks:
	@command -v pre-commit >/dev/null 2>&1 || pip install pre-commit
	pre-commit install

build:
	cargo build --release

test:
	cargo test --workspace --release

test-unit:
	cargo test --lib --release

lint:
	cargo clippy --workspace --all-targets

fmt:
	cargo fmt --all

fmt-check:
	cargo fmt --all -- --check

clean:
	cargo clean
