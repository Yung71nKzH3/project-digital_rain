import curses
import time
import json
import os
import sys

# --- Configuration ---
NOTE_INDENT_WIDTH = 4
SAVE_FILENAME = "notes.json" # Default, usually overwritten by arguments

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
        return Note(data.get("content", ""), data.get("indent", 0))

def get_flat_list(notes_tree):
    """
    Returns a flat list of all notes.
    """
    return notes_tree

def draw_notes(stdscr, flat_notes, selected_index, scroll_offset, color_pair):
    """Draws notes within the visible viewport based on scroll_offset."""
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    
    # Reserve 1 line at the bottom for safety
    max_draw_lines = height - 1 
    
    # Slice the list to get only the notes that should be visible
    visible_notes = flat_notes[scroll_offset : scroll_offset + max_draw_lines]
    
    for i, note in enumerate(visible_notes):
        # The Y position on screen (0 to max_draw_lines)
        screen_y = i
        
        # The actual index in the main list
        real_index = scroll_offset + i
        
        prefix = ""
        if note.indent > 0:
            prefix = " " * (note.indent * NOTE_INDENT_WIDTH) + "|_"

        # Draw the note
        if real_index == selected_index:
            # Highlight current selection
            try:
                stdscr.addstr(screen_y, 0, "> ", curses.A_REVERSE)
                stdscr.addstr(screen_y, 2, prefix + note.content, color_pair)
            except curses.error:
                pass 
        else:
            try:
                stdscr.addstr(screen_y, 0, "  " + prefix + note.content, color_pair)
            except curses.error:
                pass

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
    return [Note("", 0)] # Start with a blank note if file missing or corrupt


def main(stdscr):
    global SAVE_FILENAME

    # Check for filename argument
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
        
        # State variables
        selected_index = 0
        scroll_offset = 0
        
        while True:
            flat_notes = get_flat_list(notes)
            
            # Ensure there's always at least one note
            if not flat_notes:
                notes = [Note("", 0)]
                flat_notes = notes
                selected_index = 0
            
            # Bounds check selection
            if selected_index >= len(flat_notes):
                selected_index = len(flat_notes) - 1
            if selected_index < 0:
                selected_index = 0

            # --- Scroll Logic ---
            height, width = stdscr.getmaxyx()
            max_displayable = height - 1
            
            # 1. If selection is above the view, scroll up
            if selected_index < scroll_offset:
                scroll_offset = selected_index
            
            # 2. If selection is below the view, scroll down
            elif selected_index >= scroll_offset + max_displayable:
                scroll_offset = selected_index - max_displayable + 1
            # --------------------
            
            draw_notes(stdscr, flat_notes, selected_index, scroll_offset, color_pair)
            
            current_note = flat_notes[selected_index]

            # Calculate where to put the blinking terminal cursor
            cursor_y_on_screen = selected_index - scroll_offset
            
            # Calculate X position based on indentation
            # Base offset is 2 (for the "> " or "  ")
            cursor_x = 2 
            if current_note.indent > 0:
                # Add indentation spaces + the "|_" marker
                cursor_x += (current_note.indent * NOTE_INDENT_WIDTH) + 2
            
            # Add length of content
            cursor_x += len(current_note.content)

            # Safety check before moving cursor
            if 0 <= cursor_y_on_screen < height and 0 <= cursor_x < width:
                try:
                    stdscr.move(cursor_y_on_screen, cursor_x)
                except curses.error:
                    pass
            
            key = stdscr.getch()

            if key in [ord('q'), ord('Q')]:
                break
            elif key == curses.KEY_ENTER or key == ord('\n'):
                new_note = Note("", current_note.indent)
                notes.insert(selected_index + 1, new_note)
                selected_index += 1
            elif key == curses.KEY_BACKSPACE or key == ord('\b') or key == curses.KEY_DC:
                if len(current_note.content) > 0:
                    current_note.content = current_note.content[:-1]
                elif len(notes) > 1:
                    notes.remove(current_note)
                    # Move selection up if we delete a note
                    selected_index = max(0, selected_index - 1)
            elif key == curses.KEY_RIGHT:
                if current_note.indent < 5: # Limit indentation
                    current_note.indent += 1
            elif key == curses.KEY_LEFT:
                if current_note.indent > 0:
                    current_note.indent -= 1
            elif key == curses.KEY_UP:
                selected_index = max(0, selected_index - 1)
            elif key == curses.KEY_DOWN:
                selected_index = min(len(notes) - 1, selected_index + 1)
            elif 32 <= key < 127:
                current_note.content += chr(key)

    finally:
        save_notes(notes)

if __name__ == '__main__':
    curses.wrapper(main)