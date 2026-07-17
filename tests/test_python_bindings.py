"""Test Python bindings for StatGuardian Rust core."""

import pytest


def test_statguardian_import():
    """Verify Python bindings are accessible."""
    try:
        import statguardian
        assert statguardian is not None
    except ImportError:
        pytest.skip("statguardian bindings not built yet (run maturin develop)")


def test_statguardian_version():
    """Verify version is set."""
    try:
        import statguardian
        assert hasattr(statguardian, "__version__")
    except ImportError:
        pytest.skip("statguardian bindings not built yet")
