# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for GUI layout construction without a display server."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import wordle_gui_layout


def test_layout_creates_tabs_and_connects_controls(monkeypatch):
    gui = SimpleNamespace(
        root=MagicMock(), word_length=5, side_panel_width=340, side_panel_wrap=290,
        title_font=('Georgia', 26), subtitle_font=('Georgia', 12), body_font=('Helvetica', 11),
    )
    callbacks = wordle_gui_layout.LayoutCallbacks(
        tab_changed=MagicMock(), card=MagicMock(side_effect=lambda *args, **kwargs: MagicMock()),
        build_board=MagicMock(side_effect=[['play board'], ['solve board']]),
        submit_play_guess=MagicMock(), new_play_game=MagicMock(),
        submit_solver_round=MagicMock(), reset_solver=MagicMock(),
    )
    for name in ('Frame', 'Label', 'Entry', 'StringVar'):
        monkeypatch.setattr(
            wordle_gui_layout.tk, name,
            MagicMock(side_effect=lambda *args, **kwargs: MagicMock()),
        )
    buttons = MagicMock(side_effect=lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(wordle_gui_layout.tk, 'Button', buttons)
    monkeypatch.setattr(wordle_gui_layout.ttk, 'Style', MagicMock())
    monkeypatch.setattr(wordle_gui_layout.ttk, 'Notebook', MagicMock())

    wordle_gui_layout.build_layout(gui, callbacks)

    assert gui.notebook.add.call_count == 2
    gui.notebook.bind.assert_called_once_with('<<NotebookTabChanged>>', callbacks.tab_changed)
    assert gui.play_cells == ['play board']
    assert gui.solve_cells == ['solve board']
    assert [call.kwargs['command'] for call in buttons.call_args_list] == [
        callbacks.submit_play_guess, callbacks.new_play_game,
        callbacks.submit_solver_round, callbacks.reset_solver,
    ]
    gui.play_guess_entry.bind.call_args.args[1](None)
    gui.solve_guess_entry.bind.call_args.args[1](None)
    gui.solve_clue_entry.bind.call_args.args[1](None)
    callbacks.submit_play_guess.assert_called_once_with()
    assert callbacks.submit_solver_round.call_count == 2
