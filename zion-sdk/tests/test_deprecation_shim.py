"""Tests for the ``acadia_sdk`` → ``zion_sdk`` deprecation shim.

The shim must emit a ``DeprecationWarning`` on import and re-export the full
public surface of :mod:`zion_sdk`. Each test re-imports ``acadia_sdk`` via
``importlib`` so the warning fires every time (an already-cached module would
not re-execute the top-level ``warnings.warn``).
"""
from __future__ import annotations

import importlib
import sys
import warnings

import zion_sdk

# The global ``filterwarnings = ["ignore::DeprecationWarning"]`` in pyproject
# swallows deprecation warnings elsewhere; ``pytest.warns`` overrides that
# filter for the matched context, so the shim's warning is observable here.
import pytest


def _fresh_import_acadia_sdk() -> "importlib.types.ModuleType":
    """Import ``acadia_sdk`` from scratch so its top-level warning re-fires."""
    sys.modules.pop("acadia_sdk", None)
    return importlib.import_module("acadia_sdk")


def test_import_warns_deprecation() -> None:
    with pytest.warns(DeprecationWarning, match="renamed to 'zion_sdk'"):
        mod = _fresh_import_acadia_sdk()
    assert mod is not None


def test_reexported_names_match_zion_sdk() -> None:
    with pytest.warns(DeprecationWarning):
        shim = _fresh_import_acadia_sdk()
    assert set(shim.__all__) == set(zion_sdk.__all__)
    # Every name in zion_sdk.__all__ is present on the shim module.
    for name in zion_sdk.__all__:
        assert hasattr(shim, name), f"shim missing re-exported name: {name!r}"
        # The re-exported object must be the very same object as in zion_sdk.
        assert getattr(shim, name) is getattr(zion_sdk, name), (
            f"shim.{name} is not zion_sdk.{name}"
        )


def test_shim_all_is_list_of_strings() -> None:
    with pytest.warns(DeprecationWarning):
        shim = _fresh_import_acadia_sdk()
    assert isinstance(shim.__all__, list)
    assert all(isinstance(n, str) for n in shim.__all__)


def test_zion_sdk_import_does_not_warn() -> None:
    """Importing the new name must NOT emit a DeprecationWarning.

    Re-importing the already-cached module would not re-trigger warnings
    anyway, so pop it first to exercise the top-level statement again.
    """
    sys.modules.pop("zion_sdk", None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        importlib.import_module("zion_sdk")
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations == [], (
        "importing 'zion_sdk' emitted an unexpected DeprecationWarning: "
        f"{[str(w.message) for w in deprecations]}"
    )