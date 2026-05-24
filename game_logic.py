# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Coordinate setup and round-by-round Wordle game flow.

This module selects the active mode, validates startup state, chooses the
answer when needed, and runs the main game loop.
"""

from mytypes import WordSet
from dictionary import build_dictionaries
from clues import Clues
from logic import Logic
from myconcurrent import random_word


def obtain_answer(legal_answers: WordSet) -> str:
    """
    Select or validate the answer word based on mode.

    Args:
        legal_answers (WordSet): Valid answer words.

    Returns:
        str: The chosen answer.
    """
    from config import Config
    config = Config()
    mode = config.get_mode()
    answer = config.get_answer()
    word_length = config.get_word_length()
    if mode in {'auto', 'play'}:
        if not answer:
            answer = random_word(legal_answers)
            config.set_answer(answer)
            if mode == 'auto':
                import logging
                logging.info('Chose %s as the answer.', answer.upper())
        elif answer not in legal_answers:
            import logging
            if len(answer) != word_length:
                logging.error(
                    '%s is not in the dictionary and has %d letters (expected %d).',
                    answer, len(answer), word_length)
                import sys
                sys.exit(1)
            else:
                logging.error('%s is not a recognized word. Treating it as a custom answer.', answer)
                legal_answers.add(answer)
    return answer


def setup_initial_guess(start: str, word_length: int, legal_guesses: WordSet, legal_answers: WordSet, logger) -> tuple[str, Logic]:
    """
    Set up the initial guess and logic for the game.
    """
    from config import Config
    config = Config()
    guess = ''
    logic = Logic()
    if start == 'list':
        start_word_list = config.get_first_guess_words() if word_length == 5 else legal_answers
        guess = random_word(start_word_list)
        logic.update('predefined list', 0, start_word_list)
    else:
        guess = start
        logic.update('starting word provided', 0, {start})

    # Make sure the starting guess is legit, unless we are in debug mode
    if (guess not in legal_guesses and logger.getEffectiveLevel() != 10):  # logging.DEBUG
        import logging
        logging.error('%s is not a recognized word\n', guess)

    return guess, logic


def select_game_mode():
    """
    Select the appropriate game mode class based on configuration.
    """
    from config import Config
    from game_modes import ModeAdvise, ModeClues, Mode, ModePlay
    config = Config()
    mode = config.get_mode() or 'auto'  # Default to 'auto' if empty
    return {
        'advise': ModeAdvise,
        'clues': ModeClues,
        'auto': Mode,
        'play': ModePlay}[mode]


def initialize_game() -> tuple[WordSet, WordSet, Clues, str, str, Logic, type]:
    """
    Initialize the game state and setup initial parameters.
    """
    from config import Config
    config = Config()
    start = config.get_start()
    word_length = config.get_word_length()
    import logging
    logger = logging.getLogger()

    (legal_guesses, legal_answers) = build_dictionaries()
    legal_answers = legal_answers.copy()

    clues = Clues()

    # Pick a random answer if none given. Make sure the answer
    # given by the user is legit.
    answer = obtain_answer(legal_answers)

    # We only have a starting word list for words of length=5
    if start == 'list' and word_length != 5:
        import logging
        logging.warning('Starting word "list" option only available for word length 5')

    guess, logic = setup_initial_guess(start, word_length, legal_guesses, legal_answers, logger)

    mode_class = select_game_mode()

    return legal_guesses, legal_answers, clues, answer, guess, logic, mode_class


def execute_game_rounds(legal_guesses: WordSet, legal_answers: WordSet, clues, answer: str, guess: str, logic: Logic, mode_class: type) -> str:
    """
    Execute the main game rounds loop until completion.
    """
    from config import Config
    config = Config()
    word_length = config.get_word_length()
    for row_num in range(1, config.get_max_guesses() + 1):
        logic = mode_class.print_raw_guess(guess, row_num, logic)
        try:
            guess = mode_class.get_user_guess(legal_guesses, guess, legal_answers, clues, logic)
        except KeyboardInterrupt:
            import logging
            logging.debug('KeyboardInterrupt while getting user guess.')
            import sys
            sys.exit(1)
        else:
            clue_list = mode_class.get_clue(guess, answer)
            clues.add_clue(guess, clue_list)
            import logging
            logging.debug('%d guess=%s %s', row_num, guess, clues)
            from user_interface import display_row
            display_row(row_num, clue_list, guess, str(logic) if config.get_mode() != 'play' else '')
            if clue_list == ['g']*word_length:
                print(f'Solved for {guess.upper()} in {row_num} guesses')
                return guess
            if row_num == config.get_max_guesses():
                print('Better luck next time!')
                if answer:
                    print(f'The answer is: {answer.upper()}')
                return guess
            legal_answers = clues.filter_words(legal_answers)
            from best_guess import best_guess
            guess, logic = best_guess(legal_guesses, legal_answers, clues)
    return guess


def game_loop() -> None:
    """
    Run the main game loop, processing guesses and clues.
    """

    legal_guesses, legal_answers, clues, answer, guess, logic, mode_class = initialize_game()

    final_guess = execute_game_rounds(legal_guesses, legal_answers, clues, answer, guess, logic, mode_class)

    # Show the final board
    from user_interface import display_board
    display_board(clues, answer if answer else final_guess)
