# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for GUI coordination that do not require a display server."""

from __future__ import annotations

import queue
import threading
import pytest
from clues import Clues

import wordle_gui
import dictionary
from config import Config


@pytest.mark.parametrize('location', ['bundled', 'working', 'missing'])
def test_gui_dictionary_resolution_outside_repository(monkeypatch, tmp_path, location):
    bundled = tmp_path / 'bundled'
    working = tmp_path / 'working'
    bundled.mkdir()
    working.mkdir()
    monkeypatch.setattr(dictionary, '__file__', str(bundled / 'dictionary.py'))
    monkeypatch.chdir(working)
    config = Config()
    config.set_word_list_dictionary('words.txt')
    fallback = tmp_path / 'fallback.txt'
    fallback.write_text('slate\n', encoding='utf-8')
    config.set_word_list_dictionary2(str(fallback))
    if location != 'missing':
        directory = bundled if location == 'bundled' else working
        (directory / 'words.txt').write_text('crane\n', encoding='utf-8')

    wordle_gui.configure_gui_defaults()

    expected = {'slate'} if location == 'missing' else {'crane'}
    assert dictionary.load_word_set_from_file(config.get_word_list_dictionary()) == expected


class FakeVariable:
    """Small stand-in for tkinter.StringVar."""

    def __init__(self, value: str = '') -> None:
        self.value = value

    def set(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


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
    gui.play_game_over = False
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
    assert not finished
    assert gui.root.scheduled == [(100, gui._poll_shutdown_complete)]

    worker.alive = False
    monkeypatch.setattr(wordle_gui, 'num_active_children', lambda: 0)
    gui._poll_shutdown_complete()

    assert gui.shutdown_status_var.value == 'Please wait.'
    assert finished == [True]


@pytest.mark.parametrize('outcome', ['play_win', 'play_loss', 'solve_win', 'solve_empty'])
def test_terminal_round_invalidates_outstanding_recommendations(outcome):
    gui = make_gui_shell()
    gui.word_length = 5
    gui.max_guesses = 1
    gui._validate_guess = lambda guess: ''
    gui._paint_row = lambda *args: None
    kind = 'play' if outcome.startswith('play') else 'solve'
    token = getattr(gui, f'{kind}_recommend_token')
    setattr(gui, f'{kind}_recommend_pending', True)
    setattr(gui, f'{kind}_cells', [])
    setattr(gui, f'{kind}_clues', Clues())
    setattr(gui, f'{kind}_remaining', {'crane'})
    setattr(gui, f'{kind}_guess_var', FakeVariable('slate' if outcome == 'play_loss' else 'crane'))
    setattr(gui, f'{kind}_status_var', FakeVariable())
    setattr(gui, f'{kind}_remaining_var', FakeVariable())
    if kind == 'play':
        gui.play_answer = 'crane'
        gui._submit_play_guess()
    else:
        gui._solver_can_compute_clue = lambda: False
        gui.solve_clue_var = FakeVariable('bbbbb' if outcome == 'solve_empty' else 'ggggg')
        gui._submit_solver_round()
    variable = getattr(gui, f'{kind}_recommendation_var')
    completed_message = variable.value
    gui.recommendation_queue.put((kind, token, 'slate', 'outdated'))
    gui.recommendation_queue.put((f'{kind}_refresh',))
    gui._poll_recommendation_queue()
    assert variable.value == completed_message
    assert not getattr(gui, f'{kind}_recommend_pending')
