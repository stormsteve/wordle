# Wordle

`wordle` is a Python Wordle solver and play tool with both CLI and Tkinter GUI modes. It can solve a known answer, narrow candidates from clue patterns, recommend guesses interactively, or let you play locally.

## Features

- CLI solver with `auto`, `clues`, `advise`, and `play` modes
- Desktop GUI launched with `--gui`
- Search and scoring helpers for choosing strong guesses
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

Run tests:

```bash
pytest
```

## Repository Layout

- `wordle.py`: main entry point
- `wordle_gui.py`: Tkinter GUI
- `game_logic.py`, `game_modes.py`, `logic.py`: gameplay flow and solver logic
- `algorithm.py`, `best_guess.py`, `second_guess.py`: guess scoring and optimization
- `dictionary.py` and `*.txt`: dictionary inputs and curated answer/guess lists
- `build_cache.py`: cache generation utility
- `tests/`: automated tests

## Data Files

The file `/usr/share/dict/american-english` is provided by Ubuntu's `wamerican` package. The local file `american-english` is derived from that source and is intentionally not tracked in Git.

The generated cache file `wordle_cache.json` is also intentionally not tracked.

## License

This project is licensed under the GNU General Public License v3.0 or later. See [LICENSE](LICENSE).
