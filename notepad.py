import curses
import time
import json
import os
import sys

# --- Configuration ---
NOTE_INDENT_WIDTH = 4
SAVE_FILENAME = "notes.json" # Default filename

# --- Data Structures ---
class Note:
    """Represents a single note in the hierarchical structure."""
    def __init__(self, content="", indent=0):
        self.content = content
        self.indent = indent

    def to_dict(self):
        """Converts the note to a dictionary for JSON serialization."""
        return {"content": self.content, "indent": self.indent}

    @staticmethod
    def from_dict(data):
        """Creates a Note object from a dictionary."""
        return Note(data["content"], data["indent"])

def get_flat_list(notes_tree):
    """
    Returns a flat list of all notes.
    """
    return notes_tree

def get_note_at_y(notes_tree, y_pos):
    """Finds the note object at the given y-coordinate in the flat list."""
    if 0 <= y_pos < len(notes_tree):
        return notes_tree[y_pos]
    return None

def draw_notes(stdscr, notes_tree, cursor_y, color_pair):
    """Draws all the notes with the specified formatting."""
    stdscr.erase()
    y_pos = 0
    flat_list = get_flat_list(notes_tree)
    
    for i, note in enumerate(flat_list):
        y_pos += 1
        
        prefix = ""
        if note.indent > 0:
            prefix = " " * (note.indent * NOTE_INDENT_WIDTH) + "|_"

        # Draw the cursor indicator
        if y_pos == cursor_y:
            stdscr.addstr(y_pos, 0, "> ", curses.A_REVERSE)
            stdscr.addstr(y_pos, 2, prefix + note.content, color_pair)
        else:
            stdscr.addstr(y_pos, 0, "  " + prefix + note.content, color_pair)

def save_notes(notes_tree):
    """Saves notes to a JSON file."""
    try:
        with open(SAVE_FILENAME, "w") as f:
            json.dump([note.to_dict() for note in notes_tree], f, indent=4)
    except Exception:
        pass

def load_notes():
    """Loads notes from a JSON file."""
    if os.path.exists(SAVE_FILENAME):
        try:
            with open(SAVE_FILENAME, "r") as f:
                data = json.load(f)
                return [Note.from_dict(item) for item in data]
        except (IOError, json.JSONDecodeError):
            pass
    return [Note("", 0)] # Start with a blank note


def main(stdscr):
    global SAVE_FILENAME

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if not filename.endswith(".json"):
            filename += ".json"
        SAVE_FILENAME = filename

    try:
        stdscr.clear()
        curses.curs_set(1)
        stdscr.nodelay(False)
        
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            color_pair = curses.color_pair(1)
        else:
            color_pair = 0

        notes = load_notes()
        cursor_y = 1
        
        while True:
            flat_notes = get_flat_list(notes)
            if not flat_notes:
                notes = [Note("", 0)]
                flat_notes = notes
                cursor_y = 1
            
            draw_notes(stdscr, notes, cursor_y, color_pair)
            
            current_note = get_note_at_y(notes, cursor_y-1)
            if not current_note:
                cursor_y = max(1, cursor_y - 1)
                current_note = get_note_at_y(notes, cursor_y-1)

            cursor_x = 2 + (current_note.indent * NOTE_INDENT_WIDTH) + len(current_note.content) + len(str(current_note.indent))
            if current_note.indent > 0:
                cursor_x += NOTE_INDENT_WIDTH - 2
            stdscr.move(cursor_y, cursor_x)
            
            key = stdscr.getch()

            if key in [ord('q'), ord('Q')]:
                break
            elif key == curses.KEY_ENTER or key == ord('\n'):
                new_note = Note("", current_note.indent)
                notes.insert(notes.index(current_note) + 1, new_note)
                cursor_y += 1
            elif key == curses.KEY_BACKSPACE or key == ord('\b') or key == curses.KEY_DC:
                if len(current_note.content) > 0:
                    current_note.content = current_note.content[:-1]
                elif len(notes) > 1:
                    notes.remove(current_note)
                    cursor_y = max(1, cursor_y - 1)
            elif key == curses.KEY_RIGHT:
                if current_note.indent < 5: # Limit indentation to avoid out of bounds errors
                    current_note.indent += 1
            elif key == curses.KEY_LEFT:
                if current_note.indent > 0:
                    current_note.indent -= 1
            elif key == curses.KEY_UP:
                cursor_y = max(1, cursor_y - 1)
            elif key == curses.KEY_DOWN:
                cursor_y = min(len(notes), cursor_y + 1)
            elif 32 <= key < 127:
                current_note.content += chr(key)

    finally:
        save_notes(notes)

if __name__ == '__main__':
    curses.wrapper(main)
