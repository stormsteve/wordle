# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for concurrent solver process coordination."""

from __future__ import annotations

import myconcurrent


def test_launch_child_passes_only_queues_to_child(monkeypatch):
    """Worker args must stay pickle-safe for forkserver/spawn start methods."""
    started_processes = []

    class FakeProcess:
        def __init__(self, target, args):
            self.target = target
            self.args = args
            self.started = False
            started_processes.append(self)

        def start(self):
            self.started = True

    concurrent = myconcurrent.Concurrent()
    monkeypatch.setattr(myconcurrent, "Process", FakeProcess)

    try:
        myconcurrent.launch_child(concurrent, {"basil"}, 3)

        process = started_processes[0]
        assert process.target is myconcurrent.get_guess_score
        assert process.args == (
            concurrent.get_outqueue(),
            concurrent.get_inqueue(),
            {"basil"},
            3,
        )
        assert concurrent not in process.args
        assert process.started
    finally:
        concurrent.close()
