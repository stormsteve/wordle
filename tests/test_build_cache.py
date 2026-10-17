# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for cache-building progress output."""

import shutil

import build_cache


def test_print_scores_uses_fallback_terminal_width(monkeypatch):
    calls = []
    original = shutil.get_terminal_size

    def get_terminal_size(fallback=(80, 24)):
        calls.append(fallback)
        return original(fallback=fallback)

    monkeypatch.setattr(build_cache.shutil, "get_terminal_size", get_terminal_size)

    build_cache.print_scores({"crane": 4}, {"crane": 1}, -1)

    assert calls == [(80, 24)]
