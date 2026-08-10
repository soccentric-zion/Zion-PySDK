"""Deprecated compatibility shim for the renamed :mod:`zion_sdk` package.

The SDK was renamed from ``acadia-sdk`` (import ``acadia_sdk``) to
``zion-sdk`` (import ``zion_sdk``). Importing ``acadia_sdk`` now emits a
:class:`DeprecationWarning` and lazily re-exports the public surface of
:mod:`zion_sdk` so existing callers keep working while they migrate.

New code should ``import zion_sdk`` instead.

The re-export is *lazy*: ``import acadia_sdk`` always succeeds and warns (the
:class:`DeprecationWarning` fires eagerly, in the module body), but the public
names themselves are resolved on first access via module-level ``__getattr__``
(PEP 562). This keeps the shim robust to the bootstrap window where
``zion_sdk``'s generated stubs may be absent — ``import acadia_sdk`` still
works, and accessing a name ``zion_sdk`` cannot provide raises the same error
``zion_sdk`` itself would raise.
"""
from __future__ import annotations

import warnings as _warnings
from typing import Any

_warnings.warn(
    "The 'acadia_sdk' package has been renamed to 'zion_sdk'. "
    "Please update your imports to use 'zion_sdk'; 'acadia_sdk' will be "
    "removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

import zion_sdk as _zion_sdk  # noqa: E402

# Mirror zion_sdk's public surface so `acadia_sdk.__all__` matches and
# `from acadia_sdk import *` re-exports the same names. ``zion_sdk.__all__``
# is a module-level literal and is always defined, even during the bootstrap
# window where generated stubs are missing, so this is safe to copy eagerly.
__all__ = list(_zion_sdk.__all__)


def __getattr__(name: str) -> Any:
    """Lazily resolve a public name via :mod:`zion_sdk` on first access.

    Only invoked when normal attribute lookup on this module fails (i.e. the
    name is not defined here directly). Proxies to ``zion_sdk`` so the
    returned object is the very same object ``zion_sdk`` exposes, and so a
    name ``zion_sdk`` cannot provide raises an ``AttributeError`` matching
    ``zion_sdk``'s own behaviour.
    """
    try:
        return getattr(_zion_sdk, name)
    except AttributeError:
        raise AttributeError(f"module 'acadia_sdk' has no attribute {name!r}") from None


def __dir__() -> list[str]:
    """Make the shim's public names discoverable (e.g. ``dir(acadia_sdk)``)."""
    return sorted(set(globals()) | set(__all__))