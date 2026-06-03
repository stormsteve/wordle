# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Coordinate worker processes used for parallel guess scoring.

This module manages child-process queues, lifecycle helpers, and shutdown
behavior for concurrent solver work.
"""

from __future__ import annotations

from multiprocessing import Process, Queue
from queue import Empty
from sys import exit # pylint: disable=redefined-builtin
from threading import Lock


_active_concurrent_lock = Lock()
_active_concurrent: set["Concurrent"] = set()
_shutdown_requested = False


class Concurrent:
    """
    Hold worker processes and the queues they share.

    This wrapper centralizes lifecycle management so callers can launch,
    monitor, and clean up child scorer processes consistently.
    """
    def __init__(self) -> None:
        self._processes:list[Process] = []
        self._inqueue: Queue[str] = Queue() # pylint: disable=unsubscriptable-object
        self._outqueue: Queue[str] = Queue() # pylint: disable=unsubscriptable-object
        with _active_concurrent_lock:
            _active_concurrent.add(self)

    def add_process(self, p:Process) -> None:
        """Register a newly created process"""
        self._processes.append(p)

    def join_processes(self) -> None:
        """Join all of the child processes"""
        for p in self._processes:
            p.join()
        self.close()

    def get_inqueue(self) -> Queue[str]: # pylint: disable=unsubscriptable-object
        """Get the inqueue"""
        return self._inqueue

    def get_outqueue(self) -> Queue[str]: # pylint: disable=unsubscriptable-object
        """Get the outqueue"""
        return self._outqueue

    def get_num_alive(self) -> int:
        """Return the number of processes still running."""
        return sum(p.is_alive() for p in self._processes)

    def is_child_abnormal_exit(self) -> bool:
        """Look for abnormally terminated child processes"""
        if _shutdown_requested:
            return False
        for p in self._processes:
            if p.exitcode is not None and p.exitcode != 0:
                print(f'Process {p} abnormal exit code.')
                return True
        return False

    def kill_children(self) -> None:
        """Forcibly kill/terminate child processes"""
        for p in self._processes:
            p.kill()

    def clean_up_dirty(self, exit_code:int) -> None:
        """Clean up child processes and queues and then exit"""
        self._inqueue.cancel_join_thread()
        self._outqueue.cancel_join_thread()
        self.kill_children()
        self.close()
        exit(exit_code)

    def close(self) -> None:
        """Unregister this instance from the active concurrent registry."""
        with _active_concurrent_lock:
            _active_concurrent.discard(self)


def shutdown_active_children() -> None:
    """Kill any active child scorer processes."""
    global _shutdown_requested
    _shutdown_requested = True
    with _active_concurrent_lock:
        active = list(_active_concurrent)
    for concurrent in active:
        concurrent.kill_children()
        concurrent.close()


def num_active_children() -> int:
    """Return the total number of live scorer child processes."""
    with _active_concurrent_lock:
        active = list(_active_concurrent)
    return sum(concurrent.get_num_alive() for concurrent in active)


# Additional imports needed for the functions below
import logging
import psutil
from algorithm import accurate
from mytypes import WordSet
from config import Config


def get_guess_score(
        outqueue: Queue[str], # pylint: disable=unsubscriptable-object
        inqueue: Queue[str],  # pylint: disable=unsubscriptable-object
        words: WordSet,
        pid: int) -> bool:
    """
    Child process function to compute and score guesses.

    Processes guesses from the input queue, calculates their scores, and sends results to output queue.
    Exits if CPU load is too high.

    Args:
        outqueue (Queue[str]): Queue of guesses to score.
        inqueue (Queue[str]): Queue for score results.
        words (WordSet): The set of possible answers.
        pid (int): Process ID for load checking.

    Returns:
        bool: True if process completed successfully.
    """
    config = Config()
    min_score = config.get_max_word_score()
    psutil.cpu_percent() # First call always returns 0.0, so ignore the result
    while True:
        try:
            guess = outqueue.get(block = True, timeout = 0.25)
            score = accurate(words, guess, min_score)
            # Send our new lowest-score guess to the master. Include tries for logging
            if score <= min_score:
                inqueue.put(f'{guess}:{score}')
                min_score = score
                # Exit this process if the load is too high, but make sure to leave at least 1
                # child running. We do the check here so that it doesn't happen too often
                if pid > 0: # Don't stop process 0 until the in-queue is empty
                    if psutil.cpu_percent() > config.get_max_cpu_percent():
                        break
        except Empty:
            break
        except KeyboardInterrupt:
            return False
    return True


def fill_queue(conc: Concurrent, all_guesses: WordSet) -> None:
    """
    Add all guesses to the input queue for processing.

    Args:
        conc (Concurrent): The concurrent processing object.
        all_guesses (WordSet): The set of guesses to queue.
    """
    for w in all_guesses:
        conc.get_outqueue().put(w)


def launch_child(conc: Concurrent, words: WordSet, pid: int) -> None:
    """
    Start a child process to handle guess scoring.

    Args:
        conc (Concurrent): The concurrent processing object.
        words (WordSet): The set of possible answers.
        pid (int): Process ID.
    """
    p = Process(target = get_guess_score,
                args = (conc.get_outqueue(), conc.get_inqueue(), words, pid))
    p.start()
    conc.add_process(p)


def launch_children(conc: Concurrent, words: WordSet) -> None:
    """
    Start multiple child processes for parallel guess scoring.

    Launches up to the configured number of processes or the number of words, whichever is smaller.

    Args:
        conc (Concurrent): The concurrent processing object.
        words (WordSet): The set of possible answers.
    """
    config = Config()
    num_processes = min(config.get_max_child_processes(), len(words))
    logging.info('Starting %d processes', num_processes)
    for proc_num in range(num_processes):
        launch_child(conc, words, proc_num)


def process_accurate_logic_single_threaded(all_guesses: WordSet, words: WordSet) -> dict[str, float]:
    """
    Process all guesses sequentially to find the best one.

    Args:
        all_guesses (WordSet): Guesses to evaluate.
        words (WordSet): Possible answers.

    Returns:
        dict[str, float]: Dictionary of guess to score mappings.
    """
    config = Config()
    scores: dict[str, float] = {}
    # Only a few legal answers? Then processes them immediately and return the scores.
    min_score = config.get_max_word_score()
    for guess in all_guesses:
        score = accurate(words, guess, min_score)
        # Did we find our new lowest-score guess? Include ties for logging
        if score <= min_score:
            min_score = score
            scores[guess] = score
            logging.debug('guess=%s score=%s', guess, round(score, 3))
    return scores


def collect_results_from_processes(concurrent: Concurrent, scores: dict[str, float], words: WordSet) -> None:
    """
    Collect results from child processes and manage dynamic process scaling.
    """
    config = Config()
    last_log = False
    proc_num = num_alive = concurrent.get_num_alive()
    while True:
        try:
            word_and_score = concurrent.get_inqueue().get(block = True, timeout = 0.1)
            # We got a result. Process it.
            last_log = False
            guess, score_str = word_and_score.split(':')
            scores[guess] = float(score_str)
            logging.debug('guess=%s score=%s', guess, round(scores[guess], 3))
        except Empty:
            try:
                # Nothing in the queue. Check if we are done. Check our system load.
                if not (num_alive := concurrent.get_num_alive()):
                    break
                # Start another child process if the load is too low
                cpu = psutil.cpu_percent(interval = 0.2)
                # Only log a message and launch new children if we've done processing
                # since the last time we checked.
                if not last_log:
                    last_log = True
                    if (num_alive < config.get_max_child_processes() and cpu < config.get_max_cpu_percent() * 0.67):
                        proc_num += 1
                        logging.debug('Launching new child process %s to the existing %d, '
                                      'CPU: %.1f%%', proc_num, num_alive, cpu)
                        launch_child(concurrent, words, proc_num)
                    else:
                        logging.debug('Processes alive: %d, CPU: %.1f%%', num_alive, cpu)
            except KeyboardInterrupt:
                logging.debug('KeyboardInterrupt caught computing load.')
                concurrent.clean_up_dirty(1)
                break
        except KeyboardInterrupt:
            logging.debug('KeyboardInterrupt caught processing queue.')
            concurrent.clean_up_dirty(1)
            break


def process_parallel_guesses(all_guesses: WordSet, words: WordSet) -> dict[str, float]:
    """
    Process guesses using parallel child processes.
    """
    scores: dict[str, float] = {}
    concurrent = Concurrent()
    try:
        # Queue-up the words to check
        fill_queue(concurrent, all_guesses)

        # Launch the child jobs
        launch_children(concurrent, words)

        # Collect results and manage processes
        collect_results_from_processes(concurrent, scores, words)

        # Clean up the child processes
        if not _shutdown_requested and concurrent.is_child_abnormal_exit():
            logging.debug('Child process error.')
            concurrent.clean_up_dirty(2)
        concurrent.join_processes()
    finally:
        concurrent.close()
    return scores


def process_accurate_logic(all_guesses: WordSet, words: WordSet) -> dict[str, float]:
    """
    Process guesses using parallel processing if beneficial.

    Falls back to single-threaded if not enough words or processes.

    Args:
        all_guesses (WordSet): Guesses to evaluate.
        words (WordSet): Possible answers.

    Returns:
        dict[str, float]: Dictionary of guess to score mappings.
    """
    config = Config()
    max_child_processes = config.get_max_child_processes()
    # Only a few legal answers? Then processes them immediately and return the scores.
    if (len(words) < config.get_multi_processes_threshold() or max_child_processes < 2):
        return process_accurate_logic_single_threaded(all_guesses, words)

    return process_parallel_guesses(all_guesses, words)


def random_word(words: WordSet) -> str:
    """
    Select and return a random word from the given set of words.

    Args:
        words (WordSet): A set of words to choose from.

    Returns:
        str: A randomly selected word.
    """
    import random
    return random.choice(list(words))
