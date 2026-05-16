#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Wordle Solver

A Python program to solve NYT Wordle puzzles using optimal guessing strategies.
Supports multiple modes including automatic solving, clue-based solving, advice mode, and interactive play.
"""

import logging
import sys

from argument_parser import parse_command_line
from game_logic import game_loop


def main() -> None:
    """
    Main entry point: set up logging, parse args, and start the game.
    """

    logging.basicConfig(level = logging.ERROR, format = '[%(levelname)s] %(asctime)s - %(message)s')

    if '--gui' in sys.argv:
        sys.argv.remove('--gui')
        parse_command_line()
        from wordle_gui import main as gui_main
        gui_main()
        return

    parse_command_line()

    # Play the game!
    game_loop()

if __name__ == '__main__':
    main()
