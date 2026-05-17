#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Find Spelling Bee words')
    parser.add_argument('center_letter', help='Center letter (must be lowercase)')
    parser.add_argument('other_letters', help='Other 6 letters (must be lowercase)')
    parser.add_argument('--dict', default='american-english',
                        help='Path to word dictionary (default: american-english)')

    args = parser.parse_args()

    # Validate inputs are lowercase letters only
    center = args.center_letter
    others = args.other_letters

    if not (center.isalpha() and len(center) == 1 and center.islower()):
        print("Error: center_letter must be a single lowercase letter")
        sys.exit(1)

    if not (others.isalpha() and len(others) == 6 and others.islower()):
        print("Error: other_letters must be exactly 6 lowercase letters")
        sys.exit(1)

    # Combine all allowed letters
    allowed = set(center + others)
    if len(allowed) != 7:
        print("Error: Must provide exactly 7 unique letters total")
        sys.exit(1)

    # Read dictionary
    try:
        with open(args.dict, 'r') as f:
            words = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Error: Dictionary file '{args.dict}' not found")
        sys.exit(1)

    # ANSI escape codes for bold
    BOLD = '\033[1m'
    RESET = '\033[0m'

    valid_words = []
    pangrams = []

    for word in words:
        word_set = set(word)

        # Must contain center, only use allowed letters, >= 4 chars
        if (center in word and
            word_set.issubset(allowed) and
            len(word) >= 4):

            valid_words.append(word)

            # Check if pangram (uses all 7 letters)
            if word_set == allowed:
                pangrams.append(word)

    # Print results, pangrams in bold
    for word in sorted(valid_words):
        if word in pangrams:
            print(f"{BOLD}{word}{RESET}")
        else:
            print(word)

if __name__ == "__main__":
    main()
