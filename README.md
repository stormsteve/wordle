# Wordle

Everything Wordle -- Play, Solve, Assist

`wordle` is a Python toolkit for Wordle: solve known answers, narrow candidates from clue patterns, get interactive guess advice, or play locally through either the CLI or the Tkinter GUI.

## Features

- CLI solver with `auto`, `clues`, `advise`, and `play` modes
- Desktop GUI launched with `--gui`
- Search and scoring helpers for choosing strong guesses
- Adjustable word length for Wordle-like variants
- Parallel processing support for heavier guess evaluation
- Selectable optimization algorithms for guess scoring
- Configurable dictionary input files
- Optional cache builder for second-guess performance
- Test suite covering the main solver and interface modules

## Requirements

- Python 3.12 or newer recommended
- `psutil`
- `colorama`
- `tkinter` for the GUI

Install runtime dependencies with:

```bash
pip install -r requirements.txt
```

Install test dependencies with:

```bash
pip install -r requirements-dev.txt
```

## Quick Start

Run the CLI:

```bash
python3 wordle.py
```

Launch the GUI:

```bash
python3 wordle.py --gui
```

Solve for a known answer:

```bash
python3 wordle.py --mode auto --answer crane
```

Get interactive solving help:

```bash
python3 wordle.py --mode advise
```

Use a custom word length:

```bash
python3 wordle.py --length 6
```

Choose a different scoring algorithm:

```bash
python3 wordle.py --rate-alg 2
```

Increase worker processes for heavier searches:

```bash
python3 wordle.py --processes 8
```

Run tests:

```bash
pytest
```

## Capabilities

- `--length` supports Wordle-like puzzles beyond the default 5-letter game
- `--mode auto` solves for a known answer
- `--mode clues` narrows candidates from clue patterns you enter
- `--mode advise` recommends guesses while you play elsewhere
- `--mode play` lets you play locally
- `--rate-alg` switches between available guess-rating strategies
- `--processes` controls parallel worker usage for more expensive searches
- `--dictionary` lets you point the solver at a different source word list

## Cache Builder

`build_cache.py` precomputes second-guess cache data and writes it to `wordle_cache.json`. This can improve solver performance for runs that use cached second-guess lookups.

While building the cache, it also evaluates the configured starting words and computes their average number of guesses across the answer set.

Run it with:

```bash
python3 build_cache.py
```

It is a batch utility rather than a normal CLI entry point, so it starts processing immediately when launched.

## Repository Layout

- `wordle.py`: main entry point
- `wordle_gui.py`: Tkinter GUI
- `game_logic.py`, `game_modes.py`, `logic.py`: gameplay flow and solver logic
- `algorithm.py`, `best_guess.py`, `second_guess.py`: guess scoring and optimization
- `dictionary.py` and `*.txt`: dictionary inputs and curated answer/guess lists
- `build_cache.py`: cache generation utility
- `spelling_bee_cheat.py`: standalone helper for NYT Spelling Bee, separate from the main Wordle solver flow
- `tests/`: automated tests

## Data Files

The file `/usr/share/dict/american-english` is provided by Ubuntu's `wamerican` package. The local file `american-english` is derived from that source and is intentionally not tracked in Git.

The generated cache file `wordle_cache.json` is also intentionally not tracked.

## License

This project is licensed under the GNU General Public License v3.0 or later. See [LICENSE](LICENSE).

## Author

Steve Gale
