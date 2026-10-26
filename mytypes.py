# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Shared type aliases used across the Wordle solver modules.
"""
from collections.abc import Collection, Iterable
from typing import Set, List

WordSet    = Set[str]     # Define a type WordSet
WordCollection = Collection[str]  # Sized word collection with membership tests
WordIterable = Iterable[str]      # Words that can be iterated over
LetterSet  = Set[str]     # Define a type LetterSet
LetterList = List[str]    # Define a type LetterList
