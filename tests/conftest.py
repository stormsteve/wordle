# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Shared pytest fixtures for the Wordle project."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the singleton config so tests do not leak state into each other."""
    from config import Config

    Config._instance = None
    Config._default_function_initialized = False
    yield
    Config._instance = None
    Config._default_function_initialized = False
