"""Smoke tests for kalshibook package importability."""

from __future__ import annotations

import importlib.resources
import inspect


def test_import_kalshibook_class() -> None:
    """from kalshibook import KalshiBook succeeds."""
    from kalshibook import KalshiBook

    assert KalshiBook is not None


def test_import_version() -> None:
    """from kalshibook import __version__ succeeds and equals 0.1.0."""
    from kalshibook import __version__

    assert __version__ == "0.1.0"


def test_kalshibook_is_class() -> None:
    """KalshiBook is a class."""
    from kalshibook import KalshiBook

    assert inspect.isclass(KalshiBook)


def test_py_typed_marker() -> None:
    """The kalshibook package has a py.typed marker file."""
    import kalshibook

    path = importlib.resources.files(kalshibook) / "py.typed"
    assert path.is_file(), "py.typed not found in installed package"
