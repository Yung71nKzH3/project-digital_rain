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
        self.children = []

    def to_dict(self):
        """Converts the note to a dictionary for JSON serialization."""
        return {
            "content": self.content,
            "indent": self.indent,
            "children": [child.to_dict() for child in self.children]
        }

    @staticmethod
    def from_dict(data):
        """Creates a Note object from a dictionary."""
        note = Note(data["content"], data["indent"])
        note.children = [Note.from_dict(child) for child in data.get("children", [])]
        return note

def get_all_notes_and_parents(notes_tree, parent=None):
    """
    Recursively flattens a nested list of notes into a single list
    with their parent note.
    """
    flat_list = []
    for note in notes_tree:
        flat_list.append({'note': note, 'parent': parent})
        if note.children:
            flat_list.extend(get_all_notes_and_parents(note.children, parent=note))
    return flat_list

def get_note_and_parent_at_y(notes_tree, y_pos):
    """Finds the note object and its parent at the given y-coordinate."""
    flat_list = get_all_notes_and_parents(notes_tree)
    if 0 <= y_pos < len(flat_list):
        return flat_list[y_pos]['note'], flat_list[y_pos]['parent']
    return None, None

def draw_notes(stdscr, notes_tree, cursor_y, color_pair):
    """Draws all the notes with the specified formatting."""
    stdscr.erase()
    y_pos = 0
    flat_list = get_all_notes_and_parents(notes_tree)
    
    for i, item in enumerate(flat_list):
        y_pos += 1
        note = item['note']
        
        prefix = ""
        if note.indent > 0:
            prefix = " " * ((note.indent - 1) * NOTE_INDENT_WIDTH) + "|_"
        
        if y_pos == cursor_y:
            stdscr.addstr(y_pos, 0, "> ", curses.A_REVERSE)
            stdscr.addstr(y_pos, 2, prefix, color_pair)
            stdscr.addstr(y_pos, 2 + len(prefix), note.content, color_pair)
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
    if os.path.exists(SAVE_FILENAME):
        try:
            with open(SAVE_FILENAME, "r") as f:
                data = json.load(f)
                return [Note.from_dict(item) for item in data]
        except (IOError, json.JSONDecodeError):
            pass
    return [Note("", 0)]

def main(stdscr):
    global SAVE_FILENAME

    if len(sys.argv) > 1:
        # Check if the filename has a .json extension, and add it if not
        filename = sys.argv[1]
        if not filename.endswith(".json"):
            filename += ".json"
        SAVE_FILENAME = filename

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
        flat_notes_and_parents = get_all_notes_and_parents(notes)
        if not flat_notes_and_parents:
            notes = [Note("", 0)]
            flat_notes_and_parents = get_all_notes_and_parents(notes)
            cursor_y = 1
        
        draw_notes(stdscr, notes, cursor_y, color_pair)
        
        current_note, parent_note = get_note_and_parent_at_y(notes, cursor_y-1)
        if not current_note:
            cursor_y = max(1, cursor_y - 1)
            current_note, parent_note = get_note_and_parent_at_y(notes, cursor_y-1)

        cursor_x = 2 + (current_note.indent * NOTE_INDENT_WIDTH) + len(current_note.content) + len(str(current_note.indent))
        if current_note.indent > 0:
            cursor_x += NOTE_INDENT_WIDTH - 2
        stdscr.move(cursor_y, cursor_x)
        
        key = stdscr.getch()

        if key in [ord('q'), ord('Q')]:
            save_notes(notes)
            break
        elif key == curses.KEY_ENTER or key == ord('\n'):
            new_note = Note("", current_note.indent)
            if parent_note:
                parent_note.children.insert(parent_note.children.index(current_note) + 1, new_note)
            else:
                notes.insert(notes.index(current_note) + 1, new_note)
            cursor_y += 1
        elif key == curses.KEY_BACKSPACE or key == ord('\b') or key == curses.KEY_DC:
            if len(current_note.content) > 0:
                current_note.content = current_note.content[:-1]
            elif len(flat_notes_and_parents) > 1:
                if parent_note:
                    parent_note.children.remove(current_note)
                else:
                    notes.remove(current_note)
                cursor_y = max(1, cursor_y - 1)
        elif key == curses.KEY_RIGHT:
            if not parent_note and notes.index(current_note) > 0:
                parent_note_new = notes[notes.index(current_note) - 1]
                parent_note_new.children.append(current_note)
                notes.remove(current_note)
                current_note.indent += 1
        elif key == curses.KEY_LEFT:
            if parent_note:
                parent_note.children.remove(current_note)
                notes.insert(notes.index(parent_note) + 1, current_note)
                current_note.indent -= 1
        elif key == curses.KEY_UP:
            cursor_y = max(1, cursor_y - 1)
        elif key == curses.KEY_DOWN:
            cursor_y = min(len(flat_notes_and_parents), cursor_y + 1)
        elif 32 <= key < 127:
            current_note.content += chr(key)

if __name__ == '__main__':
    curses.wrapper(main)
