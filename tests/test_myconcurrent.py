# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for concurrent solver process coordination."""

from __future__ import annotations

import myconcurrent
import multiprocessing
import pytest
from config import Config
from algorithm import accurate_median


def test_launch_child_passes_pickle_safe_settings_to_child(monkeypatch):
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
            {
                'word_length': 5,
                'algorithm': Config().get_algorithm(),
                'max_word_score': 9999,
                'max_cpu_percent': 90,
            },
        )
        assert concurrent not in process.args
        assert process.started
    finally:
        concurrent.close()


@pytest.mark.parametrize('method', ['spawn', 'forkserver'])
def test_worker_preserves_length_and_scoring_algorithm(monkeypatch, method):
    if method not in multiprocessing.get_all_start_methods():
        pytest.skip(f'{method} is unavailable')
    context = multiprocessing.get_context(method)
    monkeypatch.setattr(myconcurrent, 'Queue', context.Queue)
    monkeypatch.setattr(myconcurrent, 'Process', context.Process)
    Config().set_word_length(6)
    Config().set_algorithm(accurate_median)
    concurrent = myconcurrent.Concurrent()
    try:
        concurrent.get_outqueue().put('planet')
        myconcurrent.launch_child(concurrent, {'planet', 'placer'}, 0)
        worker = concurrent._processes[0]
        worker.join(10)
        assert not worker.is_alive()
        assert worker.exitcode == 0
        guess, score = concurrent.get_inqueue().get(timeout=2).split(':')
        assert guess == 'planet'
        assert float(score) == 1.0
    finally:
        for worker in concurrent._processes:
            if worker.is_alive():
                worker.terminate()
            worker.join()
        concurrent.close()
        for channel in (concurrent.get_inqueue(), concurrent.get_outqueue()):
            channel.close()
            channel.join_thread()


def test_abnormal_worker_exit_raises_error_after_cleanup(monkeypatch):
    class AbnormalConcurrent:
        def __init__(self):
            self.terminated = False
            self.closed = False

        def get_outqueue(self):
            return object()

        def get_inqueue(self):
            return object()

        def get_num_alive(self):
            return 0

        def is_child_abnormal_exit(self):
            return True

        def terminate_children(self):
            self.terminated = True

        def close(self):
            self.closed = True

    concurrent = AbnormalConcurrent()
    monkeypatch.setattr(myconcurrent, 'Concurrent', lambda: concurrent)
    monkeypatch.setattr(myconcurrent, 'fill_queue', lambda *_args: None)
    monkeypatch.setattr(myconcurrent, 'launch_children', lambda *_args: None)
    monkeypatch.setattr(myconcurrent, 'collect_results_from_processes', lambda *_args: None)
    monkeypatch.setattr(myconcurrent, '_SHUTDOWN_REQUESTED', False)

    with pytest.raises(RuntimeError, match='scoring worker exited unexpectedly'):
        myconcurrent.process_parallel_guesses({'crane'}, {'crane', 'slate'})

    assert concurrent.terminated
    assert concurrent.closed
