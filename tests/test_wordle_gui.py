# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for GUI coordination that do not require a display server."""

from __future__ import annotations

import queue
import threading

import wordle_gui


class FakeVariable:
    """Small stand-in for tkinter.StringVar."""

    def __init__(self, value: str = '') -> None:
        self.value = value

    def set(self, value: str) -> None:
        self.value = value


class FakeRoot:
    """Record scheduled callbacks without starting Tk."""

    def __init__(self) -> None:
        self.scheduled = []

    def after(self, delay: int, callback) -> None:
        self.scheduled.append((delay, callback))


class FakeWorker:
    """Represent a tracked recommendation thread with controllable state."""

    def __init__(self, alive: bool) -> None:
        self.alive = alive

    def is_alive(self) -> bool:
        return self.alive


def make_gui_shell() -> wordle_gui.WordleGUI:
    """Create the non-Tk state needed by coordination methods."""
    gui = wordle_gui.WordleGUI.__new__(wordle_gui.WordleGUI)
    gui.root = FakeRoot()
    gui.recommendation_queue = queue.SimpleQueue()
    gui.active_recommendation_threads = set()
    gui.recommendation_thread_lock = threading.Lock()
    gui.is_closing = False
    gui.play_recommend_token = 2
    gui.solve_recommend_token = 4
    gui.play_recommendation_var = FakeVariable()
    gui.solve_recommendation_var = FakeVariable()
    return gui


def test_stale_recommendations_do_not_overwrite_newer_play_result():
    gui = make_gui_shell()

    gui._apply_play_recommendation(1, 'older', 'old result')
    assert gui.play_recommendation_var.value == ''

    gui._apply_play_recommendation(2, 'newer', 'new result')
    assert gui.play_recommendation_var.value == 'NEWER\nnew result'


def test_queue_applies_current_result_and_ignores_stale_result():
    gui = make_gui_shell()
    gui.max_guesses = 0
    gui.solve_clues = type('FakeClues', (), {'get_num_guesses': lambda self: 0})()
    gui.recommendation_queue.put(('solve', 3, 'older', 'old result'))
    gui.recommendation_queue.put(('solve', 4, 'newer', 'new result'))

    gui._poll_recommendation_queue()

    assert gui.solve_recommendation_var.value == 'NEWER\nnew result'
    assert gui.root.scheduled == [(50, gui._poll_recommendation_queue)]


def test_poll_recommendation_queue_ignores_results_while_closing():
    gui = make_gui_shell()
    gui.is_closing = True
    gui.recommendation_queue.put(('play', 2, 'guess', 'logic'))

    gui._poll_recommendation_queue()

    assert gui.play_recommendation_var.value == ''
    assert gui.root.scheduled == []


def test_active_recommendations_are_removed_after_they_finish():
    gui = make_gui_shell()
    finished = FakeWorker(alive=False)
    active = FakeWorker(alive=True)
    gui.active_recommendation_threads.update({finished, active})

    assert gui._num_active_recommendations() == 1
    assert gui.active_recommendation_threads == {active}


def test_shutdown_waits_for_threads_and_worker_processes(monkeypatch):
    gui = make_gui_shell()
    gui.shutdown_dialog = object()
    gui.shutdown_status_var = FakeVariable()
    worker = FakeWorker(alive=True)
    gui.active_recommendation_threads.add(worker)
    finished = []
    gui._finish_close = lambda: finished.append(True)
    monkeypatch.setattr(wordle_gui, 'num_active_children', lambda: 2)

    gui._poll_shutdown_complete()

    assert gui.shutdown_status_var.value == 'Waiting on 1 background task and 2 worker processes.'
    assert finished == []
    assert gui.root.scheduled == [(100, gui._poll_shutdown_complete)]

    worker.alive = False
    monkeypatch.setattr(wordle_gui, 'num_active_children', lambda: 0)
    gui._poll_shutdown_complete()

    assert gui.shutdown_status_var.value == 'Please wait.'
    assert finished == [True]
