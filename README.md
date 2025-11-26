# Digital Rain Desktop Environment (Matrix TUI)

A terminal-based "desktop environment" inspired by The Matrix. It features a falling digital rain background and integrated apps such as a hierarchical Notepad and a Tetris game — all running inside a terminal UI.

## Features
- Falling "digital rain" background effect
- Integrated Tetris game
- Simple hierarchical Notepad (auto-saves notes to JSON)
- Runs entirely in the terminal / console

## Files
Place the following files together in a single folder:
- `matrix342L.py` (main program)
- `tetris.py` (Tetris game)
- `notepad.py` (Notepad application)

## Requirements
- Python 3 (3.8+ recommended)
- psutil
- `curses` (Linux/macOS present by default)
- `windows-curses` (Windows only — see Windows instructions below)

## Installation

### Linux (Fedora)
```bash
sudo dnf install python3-psutil
# or use pip:
pip install psutil
```

### Ubuntu / Debian
```bash
sudo apt install python3-psutil
# or use pip:
pip install psutil
```

### Windows
1. Install Python from https://python.org and ensure `python`/`pip` are on your PATH.
2. Open Command Prompt and install required packages:
```cmd
pip install psutil windows-curses
```
(Note: `windows-curses` is required because Windows does not have native curses support.)

### Using pip for all platforms
If you prefer pip for dependency management:
```bash
pip install psutil
# On Windows also:
pip install windows-curses
```

## How to Run
Open your terminal, navigate to the folder containing the files, and run:
```bash
python3 matrix342L.py
```
(On Windows you may need to run `python matrix342L.py` depending on your Python installation.)

## Commands List
Type these commands directly into the Matrix interface prompt:

- `tetris`  
  Launch the Tetris game.

- `notepad`  
  Launch the Notepad application (it auto-saves notes to JSON files).

- `notepad <name>`  
  Open or create a specific note file (saved as `note_<name>.json` or similar; exact filename behavior depends on the notepad implementation).

(Replace `<name>` with your desired note name.)

## Notes & Troubleshooting
- If you see rendering issues, try a different terminal emulator or increase the terminal size.
- On Windows, ensure you installed `windows-curses` via pip; otherwise, the program will fail to import `curses`.
- If the program complains about `psutil`, reinstall it with pip: `pip install --upgrade psutil`.

## Contributing
If you'd like help improving formatting, adding a requirements file (`requirements.txt`), or opening a PR with these changes, I can prepare the commit for you.

---
Enjoy the Matrix!
