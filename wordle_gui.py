# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Desktop GUI for the Wordle solver and game.
"""

from __future__ import annotations

import pathlib
import queue
import threading
import tkinter as tk
from tkinter import ttk

from best_guess import best_guess
from clue_list import get_clue_list
from clues import Clues
from config import Config
from dictionary import build_dictionaries
from logic import Logic
from myconcurrent import num_active_children, random_word


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


def configure_gui_defaults() -> None:
    """Fill in GUI-friendly defaults without overwriting CLI options."""
    config = Config()
    if not config.get_word_length():
        config.set_word_length(5)
    if not config.get_max_guesses():
        config.set_max_guesses(6)
    if not config.get_mode():
        config.set_mode('play')
    if not config.get_start():
        config.set_start('list')

    dictionary_path = pathlib.Path(config.get_word_list_dictionary())
    if not dictionary_path.exists():
        config.set_word_list_dictionary(config.get_word_list_dictionary2())


class WordleGUI:
    """Tkinter-based front end for the existing Wordle engine."""

    def __init__(self) -> None:
        configure_gui_defaults()

        self.config = Config()
        self.word_length = self.config.get_word_length()
        self.max_guesses = self.config.get_max_guesses()
        self.configured_answer = (self.config.get_answer() or '').strip().lower()
        self.legal_guesses, self.legal_answers = build_dictionaries()
        if self._has_known_answer():
            self.legal_answers = self.legal_answers.copy()
            self.legal_answers.add(self.configured_answer)

        self.side_panel_width = max(340, 220 + (self.word_length * 22))
        self.side_panel_wrap = self.side_panel_width - 50
        window_width = max(1040, 640 + (self.word_length * 72))

        self.root = tk.Tk()
        self.root.title('Wordle GUI')
        self.root.geometry(f'{window_width}x860')
        self.root.minsize(window_width - 60, 820)
        self.root.configure(bg=COLOR_MAP['paper'])
        self.root.protocol('WM_DELETE_WINDOW', self._close_window)

        self.title_font = ('Georgia', 26, 'bold')
        self.subtitle_font = ('Georgia', 12)
        self.cell_font = ('Helvetica', 20, 'bold')
        self.body_font = ('Helvetica', 11)

        self.play_cells: list[list[tk.Label]] = []
        self.solve_cells: list[list[tk.Label]] = []
        self.play_recommend_token = 0
        self.solve_recommend_token = 0
        self.play_recommend_running = False
        self.solve_recommend_running = False
        self.play_recommend_pending = False
        self.solve_recommend_pending = False
        self.play_ready = False
        self.solve_ready = False
        self.is_closing = False
        self.shutdown_dialog: tk.Toplevel | None = None
        self.recommendation_queue: queue.SimpleQueue[tuple[str, int, str, str] | tuple[str]] = queue.SimpleQueue()
        self.active_recommendation_threads: set[threading.Thread] = set()
        self.recommendation_thread_lock = threading.Lock()

        self.play_answer = ''
        self.play_clues = Clues()
        self.play_remaining = self.legal_answers.copy()
        self.play_game_over = False

        self.solve_clues = Clues()
        self.solve_remaining = self.legal_answers.copy()

        self._build_layout()
        if self._initial_mode_uses_solver():
            self._new_play_game(recommend=False)
            self._reset_solver(recommend=True)
        else:
            self._new_play_game(recommend=True)
            self._reset_solver(recommend=False)
        self.root.after(50, self._poll_recommendation_queue)
        self.root.after_idle(self._select_initial_tab)

    def run(self) -> None:
        """Launch the event loop."""
        self.root.mainloop()

    def _close_window(self) -> None:
        """Wait for active background work to finish before closing the GUI."""
        if self.is_closing:
            return
        self.is_closing = True
        self.play_recommend_token += 1
        self.solve_recommend_token += 1
        self._show_shutdown_dialog()
        self._poll_shutdown_complete()

    def _show_shutdown_dialog(self) -> None:
        """Show a small modal while outstanding recommendation work finishes."""
        self.shutdown_dialog = tk.Toplevel(self.root)
        self.shutdown_dialog.title('Closing')
        self.shutdown_dialog.transient(self.root)
        self.shutdown_dialog.resizable(False, False)
        self.shutdown_dialog.protocol('WM_DELETE_WINDOW', lambda: None)
        self.shutdown_dialog.configure(bg=COLOR_MAP['paper'])
        self.shutdown_dialog.grab_set()
        frame = tk.Frame(self.shutdown_dialog, bg=COLOR_MAP['paper'], padx=24, pady=20)
        frame.pack(fill='both', expand=True)
        tk.Label(
            frame,
            text='Finishing background solver work...',
            font=('Georgia', 16, 'bold'),
            fg=COLOR_MAP['text'],
            bg=COLOR_MAP['paper'],
        ).pack(anchor='w')
        self.shutdown_status_var = tk.StringVar(value='Please wait.')
        tk.Label(
            frame,
            textvariable=self.shutdown_status_var,
            font=self.body_font,
            fg='#6b6256',
            bg=COLOR_MAP['paper'],
            justify='left',
        ).pack(anchor='w', pady=(10, 0))
        self.shutdown_dialog.update_idletasks()
        self.shutdown_dialog.geometry(
            f'+{self.root.winfo_rootx() + 80}+{self.root.winfo_rooty() + 80}'
        )

    def _poll_shutdown_complete(self) -> None:
        """Keep the GUI alive until in-flight recommendation work finishes."""
        active_threads = self._num_active_recommendations()
        active_children = num_active_children()
        if self.shutdown_dialog is not None and self.shutdown_status_var is not None:
            if active_threads == 0 and active_children == 0:
                message = 'Please wait.'
            else:
                parts = []
                if active_threads:
                    parts.append(f'{active_threads} background task{"s" if active_threads != 1 else ""}')
                if active_children:
                    parts.append(f'{active_children} worker process{"es" if active_children != 1 else ""}')
                message = 'Waiting on ' + ' and '.join(parts) + '.'
            self.shutdown_status_var.set(message)
        if active_threads == 0 and active_children == 0:
            self._finish_close()
            return
        self.root.after(100, self._poll_shutdown_complete)

    def _finish_close(self) -> None:
        """Destroy the GUI once all background work has completed."""
        self._clear_tk_variables()
        if self.shutdown_dialog is not None:
            try:
                self.shutdown_dialog.grab_release()
            except tk.TclError:
                pass
            self.shutdown_dialog.destroy()
            self.shutdown_dialog = None
        self.root.destroy()

    def _poll_recommendation_queue(self) -> None:
        """Apply completed recommendation results from worker threads on the Tk thread."""
        if self.is_closing:
            return
        while True:
            try:
                item = self.recommendation_queue.get_nowait()
            except queue.Empty:
                break
            if len(item) == 1:
                if item[0] == 'play_refresh':
                    self._recommend_play_guess()
                elif item[0] == 'solve_refresh':
                    self._recommend_solver_guess()
                continue
            kind, token, guess, logic_text = item
            if kind == 'play':
                self._apply_play_recommendation(token, guess, logic_text)
            else:
                self._apply_solver_recommendation(token, guess, logic_text)
        self.root.after(50, self._poll_recommendation_queue)

    def _clear_tk_variables(self) -> None:
        """Release Tk variables while the Tk main loop is still active."""
        variable_names = (
            'play_guess_var',
            'play_status_var',
            'play_recommendation_var',
            'play_remaining_var',
            'solve_guess_var',
            'solve_clue_var',
            'solve_status_var',
            'solve_recommendation_var',
            'solve_remaining_var',
            'shutdown_status_var',
        )
        for name in variable_names:
            variable = getattr(self, name, None)
            if variable is not None:
                try:
                    variable.set('')
                except tk.TclError:
                    pass
                setattr(self, name, None)

    def _register_recommendation_thread(self, worker: threading.Thread) -> None:
        """Track an in-flight recommendation thread."""
        with self.recommendation_thread_lock:
            self.active_recommendation_threads.add(worker)

    def _unregister_recommendation_thread(self, worker: threading.Thread) -> None:
        """Remove a completed recommendation thread from tracking."""
        with self.recommendation_thread_lock:
            self.active_recommendation_threads.discard(worker)

    def _num_active_recommendations(self) -> int:
        """Return the number of tracked recommendation threads still alive."""
        with self.recommendation_thread_lock:
            completed = {worker for worker in self.active_recommendation_threads if not worker.is_alive()}
            self.active_recommendation_threads.difference_update(completed)
            return len(self.active_recommendation_threads)

    def _build_layout(self) -> None:
        container = tk.Frame(self.root, bg=COLOR_MAP['paper'])
        container.pack(fill='both', expand=True, padx=18, pady=18)

        header = tk.Frame(container, bg=COLOR_MAP['paper'])
        header.pack(fill='x', pady=(0, 12))

        tk.Label(
            header,
            text='Wordle Control Room',
            font=self.title_font,
            fg=COLOR_MAP['text'],
            bg=COLOR_MAP['paper'],
        ).pack(anchor='w')
        tk.Label(
            header,
            text=f'Play against a hidden answer or drive the solver with clue patterns for {self.word_length}-letter words.',
            font=self.subtitle_font,
            fg='#5a5248',
            bg=COLOR_MAP['paper'],
        ).pack(anchor='w', pady=(4, 0))

        style = ttk.Style(self.root)
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

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill='both', expand=True)

        self.play_tab = tk.Frame(self.notebook, bg=COLOR_MAP['paper'])
        self.solve_tab = tk.Frame(self.notebook, bg=COLOR_MAP['paper'])
        self.notebook.add(self.play_tab, text='Play')
        self.notebook.add(self.solve_tab, text='Solve')
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

        self._build_play_tab()
        self._build_solve_tab()

    def _build_play_tab(self) -> None:
        top = tk.Frame(self.play_tab, bg=COLOR_MAP['paper'])
        top.pack(fill='both', expand=True, padx=8, pady=8)

        left = self._card(top)
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))

        right = self._card(top, width=self.side_panel_width)
        right.pack(side='left', fill='both')
        right.pack_propagate(False)

        tk.Label(left, text='Your board', font=('Georgia', 18, 'bold'),
                 bg='white', fg=COLOR_MAP['text']).pack(anchor='w')
        self.play_board_frame = tk.Frame(left, bg='white')
        self.play_board_frame.pack(pady=(16, 8))
        self.play_cells = self._build_board(self.play_board_frame)

        controls = tk.Frame(left, bg='white')
        controls.pack(fill='x', pady=(8, 0))
        tk.Label(controls, text='Guess', font=self.body_font,
                 bg='white', fg=COLOR_MAP['text']).pack(anchor='w')
        self.play_guess_var = tk.StringVar()
        self.play_guess_entry = tk.Entry(
            controls,
            textvariable=self.play_guess_var,
            font=('Helvetica', 18, 'bold'),
            justify='center',
            relief='solid',
            borderwidth=1,
        )
        self.play_guess_entry.pack(fill='x', pady=(4, 10))
        self.play_guess_entry.bind('<Return>', lambda _event: self._submit_play_guess())

        buttons = tk.Frame(controls, bg='white')
        buttons.pack(fill='x')
        tk.Button(
            buttons,
            text='Submit Guess',
            command=self._submit_play_guess,
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
            command=self._new_play_game,
            bg='#efe4d2',
            fg=COLOR_MAP['text'],
            activebackground='#e3d2b8',
            relief='flat',
            font=('Helvetica', 11, 'bold'),
            padx=14,
            pady=10,
        ).pack(side='left', padx=(10, 0))

        self.play_status_var = tk.StringVar()
        tk.Label(
            left,
            textvariable=self.play_status_var,
            font=self.body_font,
            bg='white',
            fg='#6b6256',
            wraplength=460,
            justify='left',
        ).pack(anchor='w', pady=(14, 0))

        tk.Label(right, text='Solver wingman', font=('Georgia', 18, 'bold'),
                 bg='white', fg=COLOR_MAP['text'],
                 wraplength=self.side_panel_wrap, justify='left').pack(anchor='w')
        self.play_recommendation_var = tk.StringVar()
        tk.Label(
            right,
            textvariable=self.play_recommendation_var,
            font=('Helvetica', 16, 'bold'),
            bg='white',
            fg=COLOR_MAP['accent'],
            wraplength=self.side_panel_wrap,
            justify='left',
        ).pack(anchor='w', pady=(14, 8))
        self.play_remaining_var = tk.StringVar()
        tk.Label(
            right,
            textvariable=self.play_remaining_var,
            font=self.body_font,
            bg='white',
            fg='#6b6256',
            wraplength=self.side_panel_wrap,
            justify='left',
        ).pack(anchor='w')
        tk.Label(
            right,
            text='Tip: press Enter after typing a guess. The recommendation updates after every row.',
            font=self.body_font,
            bg='white',
            fg='#6b6256',
            wraplength=self.side_panel_wrap,
            justify='left',
        ).pack(anchor='w', pady=(20, 0))

    def _build_solve_tab(self) -> None:
        top = tk.Frame(self.solve_tab, bg=COLOR_MAP['paper'])
        top.pack(fill='both', expand=True, padx=8, pady=8)

        left = self._card(top)
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))

        right = self._card(top, width=self.side_panel_width)
        right.pack(side='left', fill='both')
        right.pack_propagate(False)

        tk.Label(left, text='Solver board', font=('Georgia', 18, 'bold'),
                 bg='white', fg=COLOR_MAP['text']).pack(anchor='w')
        self.solve_board_frame = tk.Frame(left, bg='white')
        self.solve_board_frame.pack(pady=(16, 8))
        self.solve_cells = self._build_board(self.solve_board_frame)

        form = tk.Frame(left, bg='white')
        form.pack(fill='x', pady=(8, 0))

        tk.Label(form, text='Guess', font=self.body_font,
                 bg='white', fg=COLOR_MAP['text']).grid(row=0, column=0, sticky='w')
        self.solve_clue_label = tk.Label(form, text='Clue pattern', font=self.body_font,
                                         bg='white', fg=COLOR_MAP['text'])
        self.solve_clue_label.grid(row=0, column=1, sticky='w', padx=(12, 0))

        self.solve_guess_var = tk.StringVar()
        self.solve_clue_var = tk.StringVar()
        self.solve_guess_entry = tk.Entry(
            form,
            textvariable=self.solve_guess_var,
            font=('Helvetica', 16, 'bold'),
            justify='center',
            relief='solid',
            borderwidth=1,
            width=10,
        )
        self.solve_guess_entry.grid(row=1, column=0, sticky='we', pady=(4, 10))
        self.solve_clue_entry = tk.Entry(
            form,
            textvariable=self.solve_clue_var,
            font=('Helvetica', 16, 'bold'),
            justify='center',
            relief='solid',
            borderwidth=1,
            width=10,
        )
        self.solve_clue_entry.grid(row=1, column=1, sticky='we', padx=(12, 0), pady=(4, 10))
        self.solve_guess_entry.bind('<Return>', lambda _event: self._submit_solver_round())
        self.solve_clue_entry.bind('<Return>', lambda _event: self._submit_solver_round())

        button_row = tk.Frame(left, bg='white')
        button_row.pack(fill='x')
        tk.Button(
            button_row,
            text='Add Round',
            command=self._submit_solver_round,
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
            command=self._reset_solver,
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
            text=f'Use g, y, b for green, yellow, black. Enter exactly {self.word_length} clue characters.',
            font=self.body_font,
            bg='white',
            fg='#6b6256',
            wraplength=460,
            justify='left',
        ).pack(anchor='w', pady=(14, 0))
        self.solve_status_var = tk.StringVar()
        tk.Label(
            left,
            textvariable=self.solve_status_var,
            font=self.body_font,
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
            wraplength=self.side_panel_wrap,
            justify='left',
        ).pack(anchor='w')
        self.solve_recommendation_var = tk.StringVar()
        tk.Label(
            right,
            textvariable=self.solve_recommendation_var,
            font=('Helvetica', 16, 'bold'),
            bg='white',
            fg=COLOR_MAP['accent'],
            wraplength=self.side_panel_wrap,
            justify='left',
        ).pack(anchor='w', pady=(14, 8))
        self.solve_remaining_var = tk.StringVar()
        tk.Label(
            right,
            textvariable=self.solve_remaining_var,
            font=self.body_font,
            bg='white',
            fg='#6b6256',
            wraplength=self.side_panel_wrap,
            justify='left',
        ).pack(anchor='w')

    def _card(self, parent: tk.Widget, width: int | None = None) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg='white',
            highlightbackground=COLOR_MAP['border'],
            highlightthickness=1,
            padx=18,
            pady=18,
            width=width,
        )
        return frame

    def _build_board(self, parent: tk.Widget) -> list[list[tk.Label]]:
        cells: list[list[tk.Label]] = []
        for row in range(self.max_guesses):
            row_cells: list[tk.Label] = []
            for col in range(self.word_length):
                label = tk.Label(
                    parent,
                    text='',
                    width=3,
                    height=1,
                    font=self.cell_font,
                    bg=COLOR_MAP['empty'],
                    fg=COLOR_MAP['text'],
                    relief='flat',
                    padx=12,
                    pady=12,
                )
                label.grid(row=row, column=col, padx=5, pady=5)
                row_cells.append(label)
            cells.append(row_cells)
        return cells

    def _reset_board(self, cells: list[list[tk.Label]]) -> None:
        for row in cells:
            for cell in row:
                cell.config(text='', bg=COLOR_MAP['empty'], fg=COLOR_MAP['text'])

    def _paint_row(self, cells: list[list[tk.Label]], row_num: int, guess: str, clue: list[str]) -> None:
        for index, letter in enumerate(guess):
            cells[row_num][index].config(
                text=letter.upper(),
                bg=COLOR_MAP[clue[index]],
                fg='white',
            )

    def _set_cell_word(self, cells: list[list[tk.Label]], row_num: int, word: str) -> None:
        for index, letter in enumerate(word):
            cells[row_num][index].config(
                text=letter.upper(),
                bg=COLOR_MAP['empty'],
                fg=COLOR_MAP['text'],
            )

    def _new_play_game(self, recommend: bool = True) -> None:
        self.play_answer = self.configured_answer if self._has_known_answer() else random_word(self.legal_answers)
        self.play_clues = Clues()
        self.play_remaining = self.legal_answers.copy()
        self.play_game_over = False
        self.play_guess_var.set(self._get_configured_start_guess())
        if self._has_known_answer():
            self.play_status_var.set(
                f'Loaded fixed answer {self.configured_answer.upper()}. Start with any legal {self.word_length}-letter guess.'
            )
        else:
            self.play_status_var.set(
                f'A fresh answer is ready. Start with any legal {self.word_length}-letter guess.'
            )
        self.play_remaining_var.set(f'{len(self.play_remaining)} possible answers at the start.')
        self._reset_board(self.play_cells)
        self.play_ready = recommend
        if recommend:
            self._recommend_play_guess()
        else:
            self.play_recommendation_var.set('Open the Play tab to compute a recommendation.')
        self.play_guess_entry.focus_set()

    def _submit_play_guess(self) -> None:
        if self.play_game_over:
            self.play_status_var.set('This round is finished. Start a new game to play again.')
            return

        guess = self.play_guess_var.get().strip().lower()
        error = self._validate_guess(guess)
        if error:
            self.play_status_var.set(error)
            return

        row_num = self.play_clues.get_num_guesses()
        clue = get_clue_list(guess, self.play_answer)
        self.play_clues.add_clue(guess, clue)
        self.play_remaining = self.play_clues.filter_words(self.play_remaining)
        self._paint_row(self.play_cells, row_num, guess, clue)
        self.play_guess_var.set('')

        if clue == ['g'] * self.word_length:
            self.play_game_over = True
            guesses = self.play_clues.get_num_guesses()
            self.play_status_var.set(f'Solved in {guesses} guess{"es" if guesses != 1 else ""}.')
            self.play_recommendation_var.set('Board complete.')
            self.play_remaining_var.set('Puzzle solved.')
            return

        if self.play_clues.get_num_guesses() >= self.max_guesses:
            self.play_game_over = True
            self.play_status_var.set(f'Out of guesses. The answer was {self.play_answer.upper()}.')
            self.play_recommendation_var.set('Round over.')
            self.play_remaining_var.set(f'{len(self.play_remaining)} matching answers remained.')
            return

        remaining = len(self.play_remaining)
        self.play_status_var.set(f'Guess recorded. {remaining} possible answer{"s" if remaining != 1 else ""} remain.')
        self.play_remaining_var.set(
            f'{remaining} possible answer{"s" if remaining != 1 else ""} remain after {self.play_clues.get_num_guesses()} row{"s" if self.play_clues.get_num_guesses() != 1 else ""}.'
        )
        self._recommend_play_guess()

    def _reset_solver(self, recommend: bool = True) -> None:
        self.solve_clues = Clues()
        self.solve_remaining = self.legal_answers.copy()
        self.solve_guess_var.set(self._get_configured_start_guess())
        self.solve_clue_var.set('')
        if self._solver_can_compute_clue():
            self.solve_clue_label.config(text='Computed clue')
            self.solve_clue_entry.config(state='disabled')
            self.solve_status_var.set(
                f'Known answer {self.configured_answer.upper()} loaded. Enter a {self.word_length}-letter guess and the clue will be computed for you.'
            )
        else:
            self.solve_clue_label.config(text='Clue pattern')
            self.solve_clue_entry.config(state='normal')
            self.solve_status_var.set(
                f'Enter a {self.word_length}-letter guess and the clue pattern you saw in Wordle.'
            )
        self.solve_remaining_var.set(f'{len(self.solve_remaining)} possible answers at the start.')
        self._reset_board(self.solve_cells)
        self.solve_ready = recommend
        if recommend:
            self._recommend_solver_guess()
        else:
            self.solve_recommendation_var.set('Open the Solve tab to compute a recommendation.')

    def _submit_solver_round(self) -> None:
        guess = self.solve_guess_var.get().strip().lower()

        error = self._validate_guess(guess)
        if error:
            self.solve_status_var.set(error)
            return

        row_num = self.solve_clues.get_num_guesses()
        if row_num >= self.max_guesses:
            self.solve_status_var.set(
                f'The board already has {self.max_guesses} rounds. Reset the solver to continue.'
            )
            return

        if self._solver_can_compute_clue():
            clue_list = get_clue_list(guess, self.configured_answer)
            clue = ''.join(clue_list)
            self.solve_clue_var.set(clue)
        else:
            clue = self.solve_clue_var.get().strip().lower()
            if len(clue) != self.word_length or any(letter not in {'g', 'y', 'b'} for letter in clue):
                self.solve_status_var.set(
                    f'Clue pattern must be exactly {self.word_length} characters using only g, y, and b.'
                )
                return
            clue_list = list(clue)

        self.solve_clues.add_clue(guess, clue_list)
        self.solve_remaining = self.solve_clues.filter_words(self.solve_remaining)
        self._paint_row(self.solve_cells, row_num, guess, clue_list)
        self.solve_guess_var.set('')
        if not self._solver_can_compute_clue():
            self.solve_clue_var.set('')

        remaining = len(self.solve_remaining)
        if clue == 'g' * self.word_length:
            self.solve_status_var.set(f'Solved. The answer is {guess.upper()}.')
            self.solve_recommendation_var.set('No further guess needed.')
            self.solve_remaining_var.set('Puzzle solved.')
            return

        if remaining == 0:
            self.solve_status_var.set('No answers match those clues. Double-check the clue pattern.')
            self.solve_recommendation_var.set('No valid candidate.')
            self.solve_remaining_var.set('0 possible answers remain.')
            return

        self.solve_status_var.set(
            f'Round stored. {remaining} possible answer{"s" if remaining != 1 else ""} remain.'
        )
        self.solve_remaining_var.set(
            f'{remaining} possible answer{"s" if remaining != 1 else ""} remain after {self.solve_clues.get_num_guesses()} row{"s" if self.solve_clues.get_num_guesses() != 1 else ""}.'
        )
        self._recommend_solver_guess()

    def _validate_guess(self, guess: str) -> str:
        if len(guess) != self.word_length:
            return f'Guess must be exactly {self.word_length} letters.'
        if guess not in self.legal_guesses:
            return f'{guess.upper()} is not in the legal guess list.'
        return ''

    def _recommend_play_guess(self) -> None:
        if self.play_recommend_running:
            self.play_recommend_pending = True
            self.play_recommend_token += 1
            return
        token = self.play_recommend_token + 1
        self.play_recommend_token = token
        self.play_recommend_running = True
        self.play_recommend_pending = False
        initial_guess = self._get_initial_guess(self.play_clues.get_num_guesses())
        if self.play_clues.get_num_guesses() == 0 and initial_guess:
            logic = Logic()
            logic.update(self._get_initial_guess_reason(), 0, {initial_guess})
            self.play_recommend_running = False
            self._apply_play_recommendation(token, initial_guess, str(logic))
            return
        self.play_recommendation_var.set('Computing recommendation...')
        remaining = self.play_remaining.copy()
        clues = self.play_clues

        def worker() -> None:
            try:
                guess, logic = best_guess(self.legal_guesses, remaining, clues)
                if not self.is_closing:
                    self.recommendation_queue.put(('play', token, guess, str(logic)))
            finally:
                self.play_recommend_running = False
                if self.play_recommend_pending and not self.is_closing:
                    self.recommendation_queue.put(('play_refresh',))
                self._unregister_recommendation_thread(thread)

        thread = threading.Thread(target=worker, name=f'play-recommend-{token}')
        self._register_recommendation_thread(thread)
        thread.start()

    def _apply_play_recommendation(self, token: int, guess: str, logic_text: str) -> None:
        if token != self.play_recommend_token:
            return
        self.play_recommendation_var.set(f'{guess.upper()}\n{logic_text}')

    def _recommend_solver_guess(self) -> None:
        if self.solve_recommend_running:
            self.solve_recommend_pending = True
            self.solve_recommend_token += 1
            return
        token = self.solve_recommend_token + 1
        self.solve_recommend_token = token
        self.solve_recommend_running = True
        self.solve_recommend_pending = False
        initial_guess = self._get_initial_guess(self.solve_clues.get_num_guesses())
        if self.solve_clues.get_num_guesses() == 0 and initial_guess:
            logic = Logic()
            logic.update(self._get_initial_guess_reason(), 0, {initial_guess})
            self.solve_recommend_running = False
            self._apply_solver_recommendation(token, initial_guess, str(logic))
            return
        self.solve_recommendation_var.set('Computing recommendation...')
        remaining = self.solve_remaining.copy()
        clues = self.solve_clues

        def worker() -> None:
            try:
                guess, logic = best_guess(self.legal_guesses, remaining, clues)
                if not self.is_closing:
                    self.recommendation_queue.put(('solve', token, guess, str(logic)))
            finally:
                self.solve_recommend_running = False
                if self.solve_recommend_pending and not self.is_closing:
                    self.recommendation_queue.put(('solve_refresh',))
                self._unregister_recommendation_thread(thread)

        thread = threading.Thread(target=worker, name=f'solve-recommend-{token}')
        self._register_recommendation_thread(thread)
        thread.start()

    def _apply_solver_recommendation(self, token: int, guess: str, logic_text: str) -> None:
        if token != self.solve_recommend_token:
            return
        self.solve_recommendation_var.set(f'{guess.upper()}\n{logic_text}')
        next_row = self.solve_clues.get_num_guesses()
        if next_row < self.max_guesses:
            self._set_cell_word(self.solve_cells, next_row, guess)
            self.solve_guess_var.set(guess)

    def _get_configured_start_guess(self) -> str:
        start = (self.config.get_start() or '').strip().lower()
        if start and start != 'list' and len(start) == self.word_length and start in self.legal_guesses:
            return start
        return ''

    def _get_initial_guess(self, num_guesses: int) -> str:
        """Return the cheap startup guess the CLI would use before any clues exist."""
        if num_guesses != 0:
            return ''
        configured = self._get_configured_start_guess()
        if configured:
            return configured
        if (self.config.get_start() or '').strip().lower() == 'list':
            if self.word_length == 5:
                return random_word(self.config.get_first_guess_words())
            return random_word(self.legal_answers)
        return ''

    def _get_initial_guess_reason(self) -> str:
        """Describe the source of the initial startup guess."""
        return (
            'starting word provided'
            if self._get_configured_start_guess()
            else 'predefined list'
        )

    def _on_tab_changed(self, _event=None) -> None:
        """Lazy-start recommendations for tabs that have not been activated yet."""
        current_tab = self.notebook.select()
        if current_tab == str(self.play_tab) and not self.play_ready:
            self.play_ready = True
            self._recommend_play_guess()
        elif current_tab == str(self.solve_tab) and not self.solve_ready:
            self.solve_ready = True
            self._recommend_solver_guess()

    def _has_known_answer(self) -> bool:
        return bool(self.configured_answer and len(self.configured_answer) == self.word_length)

    def _solver_can_compute_clue(self) -> bool:
        return self._has_known_answer()

    def _initial_mode_uses_solver(self) -> bool:
        return self.config.get_mode() in {'clues', 'advise'}

    def _select_initial_tab(self) -> None:
        tabs = self.notebook.tabs()
        if not tabs:
            return
        tab_id = tabs[1] if self._initial_mode_uses_solver() else tabs[0]
        self.notebook.select(tab_id)


def main() -> None:
    """Run the GUI application."""
    WordleGUI().run()


if __name__ == '__main__':
    main()
