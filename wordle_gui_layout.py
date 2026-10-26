# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Build the Tk widgets for the Wordle GUI."""

from dataclasses import dataclass
from collections.abc import Callable
import tkinter as tk
from tkinter import ttk


COLOR_MAP = {
    'g': '#5f8f52',
    'y': '#c9a227',
    'b': '#3c4048',
    'empty': '#f3eadb',
    'text': '#1c1b1a',
    'paper': '#fffaf2',
    'accent': '#d96c47',
    'border': '#d8c8b0',
}


@dataclass(frozen=True)
class LayoutCallbacks:
    """Actions supplied by the GUI controller to its widgets."""

    tab_changed: Callable
    card: Callable
    build_board: Callable
    submit_play_guess: Callable
    new_play_game: Callable
    submit_solver_round: Callable
    reset_solver: Callable


def build_layout(gui, callbacks: LayoutCallbacks) -> None:
    """Build both tabs and bind them to the controller callbacks."""
    container = tk.Frame(gui.root, bg=COLOR_MAP['paper'])
    container.pack(fill='both', expand=True, padx=18, pady=18)

    header = tk.Frame(container, bg=COLOR_MAP['paper'])
    header.pack(fill='x', pady=(0, 12))

    tk.Label(
        header,
        text='Wordle Control Room',
        font=gui.title_font,
        fg=COLOR_MAP['text'],
        bg=COLOR_MAP['paper'],
    ).pack(anchor='w')
    tk.Label(
        header,
        text=('Play against a hidden answer or drive the solver with clue patterns '
              f'for {gui.word_length}-letter words.'),
        font=gui.subtitle_font,
        fg='#5a5248',
        bg=COLOR_MAP['paper'],
    ).pack(anchor='w', pady=(4, 0))

    style = ttk.Style(gui.root)
    style.theme_use('clam')
    style.configure('TNotebook', background=COLOR_MAP['paper'], borderwidth=0)
    style.configure(
        'TNotebook.Tab',
        padding=(18, 10),
        font=('Helvetica', 11, 'bold'),
        background='#e6d7c2',
        foreground='#6b6256',
    )
    style.map(
        'TNotebook.Tab',
        background=[('selected', 'white'), ('active', '#efe4d2')],
        foreground=[('selected', COLOR_MAP['accent']), ('active', COLOR_MAP['text'])],
    )

    gui.notebook = ttk.Notebook(container)
    gui.notebook.pack(fill='both', expand=True)

    gui.play_tab = tk.Frame(gui.notebook, bg=COLOR_MAP['paper'])
    gui.solve_tab = tk.Frame(gui.notebook, bg=COLOR_MAP['paper'])
    gui.notebook.add(gui.play_tab, text='Play')
    gui.notebook.add(gui.solve_tab, text='Solve')
    gui.notebook.bind('<<NotebookTabChanged>>', callbacks.tab_changed)

    _build_play_tab(gui, callbacks)
    _build_solve_tab(gui, callbacks)


def _build_play_tab(gui, callbacks: LayoutCallbacks) -> None:
    top = tk.Frame(gui.play_tab, bg=COLOR_MAP['paper'])
    top.pack(fill='both', expand=True, padx=8, pady=8)

    left = callbacks.card(top)
    left.pack(side='left', fill='both', expand=True, padx=(0, 8))

    right = callbacks.card(top, width=gui.side_panel_width)
    right.pack(side='left', fill='both')
    right.pack_propagate(False)

    tk.Label(left, text='Your board', font=('Georgia', 18, 'bold'),
             bg='white', fg=COLOR_MAP['text']).pack(anchor='w')
    gui.play_board_frame = tk.Frame(left, bg='white')
    gui.play_board_frame.pack(pady=(16, 8))
    gui.play_cells = callbacks.build_board(gui.play_board_frame)

    controls = tk.Frame(left, bg='white')
    controls.pack(fill='x', pady=(8, 0))
    tk.Label(controls, text='Guess', font=gui.body_font,
             bg='white', fg=COLOR_MAP['text']).pack(anchor='w')
    gui.play_guess_var = tk.StringVar()
    gui.play_guess_entry = tk.Entry(
        controls,
        textvariable=gui.play_guess_var,
        font=('Helvetica', 18, 'bold'),
        justify='center',
        relief='solid',
        borderwidth=1,
    )
    gui.play_guess_entry.pack(fill='x', pady=(4, 10))
    gui.play_guess_entry.bind('<Return>', lambda _event: callbacks.submit_play_guess())

    buttons = tk.Frame(controls, bg='white')
    buttons.pack(fill='x')
    tk.Button(
        buttons,
        text='Submit Guess',
        command=callbacks.submit_play_guess,
        bg=COLOR_MAP['accent'],
        fg='white',
        activebackground='#bf5d3b',
        relief='flat',
        font=('Helvetica', 11, 'bold'),
        padx=14,
        pady=10,
    ).pack(side='left')
    tk.Button(
        buttons,
        text='New Game',
        command=callbacks.new_play_game,
        bg='#efe4d2',
        fg=COLOR_MAP['text'],
        activebackground='#e3d2b8',
        relief='flat',
        font=('Helvetica', 11, 'bold'),
        padx=14,
        pady=10,
    ).pack(side='left', padx=(10, 0))

    gui.play_status_var = tk.StringVar()
    tk.Label(
        left,
        textvariable=gui.play_status_var,
        font=gui.body_font,
        bg='white',
        fg='#6b6256',
        wraplength=460,
        justify='left',
    ).pack(anchor='w', pady=(14, 0))

    tk.Label(right, text='Solver wingman', font=('Georgia', 18, 'bold'),
             bg='white', fg=COLOR_MAP['text'],
             wraplength=gui.side_panel_wrap, justify='left').pack(anchor='w')
    gui.play_recommendation_var = tk.StringVar()
    tk.Label(
        right,
        textvariable=gui.play_recommendation_var,
        font=('Helvetica', 16, 'bold'),
        bg='white',
        fg=COLOR_MAP['accent'],
        wraplength=gui.side_panel_wrap,
        justify='left',
    ).pack(anchor='w', pady=(14, 8))
    gui.play_remaining_var = tk.StringVar()
    tk.Label(
        right,
        textvariable=gui.play_remaining_var,
        font=gui.body_font,
        bg='white',
        fg='#6b6256',
        wraplength=gui.side_panel_wrap,
        justify='left',
    ).pack(anchor='w')
    tk.Label(
        right,
        text='Tip: press Enter after typing a guess. The recommendation updates after every row.',
        font=gui.body_font,
        bg='white',
        fg='#6b6256',
        wraplength=gui.side_panel_wrap,
        justify='left',
    ).pack(anchor='w', pady=(20, 0))

def _build_solve_tab(gui, callbacks: LayoutCallbacks) -> None:
    top = tk.Frame(gui.solve_tab, bg=COLOR_MAP['paper'])
    top.pack(fill='both', expand=True, padx=8, pady=8)

    left = callbacks.card(top)
    left.pack(side='left', fill='both', expand=True, padx=(0, 8))

    right = callbacks.card(top, width=gui.side_panel_width)
    right.pack(side='left', fill='both')
    right.pack_propagate(False)

    tk.Label(left, text='Solver board', font=('Georgia', 18, 'bold'),
             bg='white', fg=COLOR_MAP['text']).pack(anchor='w')
    gui.solve_board_frame = tk.Frame(left, bg='white')
    gui.solve_board_frame.pack(pady=(16, 8))
    gui.solve_cells = callbacks.build_board(gui.solve_board_frame)

    form = tk.Frame(left, bg='white')
    form.pack(fill='x', pady=(8, 0))

    tk.Label(form, text='Guess', font=gui.body_font,
             bg='white', fg=COLOR_MAP['text']).grid(row=0, column=0, sticky='w')
    gui.solve_clue_label = tk.Label(form, text='Clue pattern', font=gui.body_font,
                                     bg='white', fg=COLOR_MAP['text'])
    gui.solve_clue_label.grid(row=0, column=1, sticky='w', padx=(12, 0))

    gui.solve_guess_var = tk.StringVar()
    gui.solve_clue_var = tk.StringVar()
    gui.solve_guess_entry = tk.Entry(
        form,
        textvariable=gui.solve_guess_var,
        font=('Helvetica', 16, 'bold'),
        justify='center',
        relief='solid',
        borderwidth=1,
        width=10,
    )
    gui.solve_guess_entry.grid(row=1, column=0, sticky='we', pady=(4, 10))
    gui.solve_clue_entry = tk.Entry(
        form,
        textvariable=gui.solve_clue_var,
        font=('Helvetica', 16, 'bold'),
        justify='center',
        relief='solid',
        borderwidth=1,
        width=10,
    )
    gui.solve_clue_entry.grid(row=1, column=1, sticky='we', padx=(12, 0), pady=(4, 10))
    gui.solve_guess_entry.bind('<Return>', lambda _event: callbacks.submit_solver_round())
    gui.solve_clue_entry.bind('<Return>', lambda _event: callbacks.submit_solver_round())

    button_row = tk.Frame(left, bg='white')
    button_row.pack(fill='x')
    tk.Button(
        button_row,
        text='Add Round',
        command=callbacks.submit_solver_round,
        bg=COLOR_MAP['accent'],
        fg='white',
        activebackground='#bf5d3b',
        relief='flat',
        font=('Helvetica', 11, 'bold'),
        padx=14,
        pady=10,
    ).pack(side='left')
    tk.Button(
        button_row,
        text='Reset Solver',
        command=callbacks.reset_solver,
        bg='#efe4d2',
        fg=COLOR_MAP['text'],
        activebackground='#e3d2b8',
        relief='flat',
        font=('Helvetica', 11, 'bold'),
        padx=14,
        pady=10,
    ).pack(side='left', padx=(10, 0))

    tk.Label(
        left,
        text=('Use g, y, b for green, yellow, black. '
              f'Enter exactly {gui.word_length} clue characters.'),
        font=gui.body_font,
        bg='white',
        fg='#6b6256',
        wraplength=460,
        justify='left',
    ).pack(anchor='w', pady=(14, 0))
    gui.solve_status_var = tk.StringVar()
    tk.Label(
        left,
        textvariable=gui.solve_status_var,
        font=gui.body_font,
        bg='white',
        fg='#6b6256',
        wraplength=460,
        justify='left',
    ).pack(anchor='w', pady=(10, 0))

    tk.Label(
        right,
        text='Next recommendation',
        font=('Georgia', 18, 'bold'),
        bg='white',
        fg=COLOR_MAP['text'],
        wraplength=gui.side_panel_wrap,
        justify='left',
    ).pack(anchor='w')
    gui.solve_recommendation_var = tk.StringVar()
    tk.Label(
        right,
        textvariable=gui.solve_recommendation_var,
        font=('Helvetica', 16, 'bold'),
        bg='white',
        fg=COLOR_MAP['accent'],
        wraplength=gui.side_panel_wrap,
        justify='left',
    ).pack(anchor='w', pady=(14, 8))
    gui.solve_remaining_var = tk.StringVar()
    tk.Label(
        right,
        textvariable=gui.solve_remaining_var,
        font=gui.body_font,
        bg='white',
        fg='#6b6256',
        wraplength=gui.side_panel_wrap,
        justify='left',
    ).pack(anchor='w')
