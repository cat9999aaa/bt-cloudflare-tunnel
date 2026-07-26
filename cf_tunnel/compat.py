from __future__ import annotations

import sys
from dataclasses import dataclass


_DATACLASS_OPTIONS = {"slots": True} if sys.version_info >= (3, 10) else {}


def frozen_dataclass(cls):
    """Create an immutable dataclass on both BaoTa Python 3.7 and modern Python."""

    return dataclass(frozen=True, **_DATACLASS_OPTIONS)(cls)
