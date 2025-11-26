import curses
import time
import json
import os
import sys

# --- Configuration ---
NOTE_INDENT_WIDTH = 4
DEFAULT_FILENAME = "notes.json"

class Note:
    def __init__(self, content="", indent=0):
        self.content = content
        self.indent = indent

    def to_dict(self):
        return {"content": self.content, "indent": self.indent}

    @staticmethod
    def from_dict(data):
        return Note(data.get("content", ""), data.get("indent", 0))

def get_flat_list(notes_tree):
    return notes_tree

def draw_notes(stdscr, flat_notes, selected_index, scroll_offset, color_pair):
    stdscr.erase()
    height, width = stdscr.getmaxyx()
    max_draw_lines = height - 1 
    visible_notes = flat_notes[scroll_offset : scroll_offset + max_draw_lines]
    
    for i, note in enumerate(visible_notes):
        screen_y = i
        real_index = scroll_offset + i
        prefix = ""
        if note.indent > 0:
            prefix = " " * (note.indent * NOTE_INDENT_WIDTH) + "|_"

        if real_index == selected_index:
            try:
                stdscr.addstr(screen_y, 0, "> ", curses.A_REVERSE)
                stdscr.addstr(screen_y, 2, prefix + note.content, color_pair)
            except curses.error: pass 
        else:
            try:
                stdscr.addstr(screen_y, 0, "  " + prefix + note.content, color_pair)
            except curses.error: pass

def save_notes(notes_tree, filename):
    try:
        with open(filename, "w") as f:
            json.dump([note.to_dict() for note in notes_tree], f, indent=4)
    except Exception:
        pass

def load_notes(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
                return [Note.from_dict(item) for item in data]
        except (IOError, json.JSONDecodeError):
            pass
    return [Note("", 0)]

def main(stdscr, filename=None):
    # If no filename passed via function, check args or default
    if filename is None:
        if len(sys.argv) > 1:
            filename = sys.argv[1]
        else:
            filename = DEFAULT_FILENAME
            
    if not filename.endswith(".json"):
        filename += ".json"

    try:
        stdscr.clear()
        curses.curs_set(1) # Show cursor
        stdscr.nodelay(False) # Blocking input for typing
        
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            color_pair = curses.color_pair(1)
        else:
            color_pair = 0

        notes = load_notes(filename)
        selected_index = 0
        scroll_offset = 0
        
        while True:
            flat_notes = get_flat_list(notes)
            if not flat_notes:
                notes = [Note("", 0)]
                flat_notes = notes
                selected_index = 0
            
            if selected_index >= len(flat_notes): selected_index = len(flat_notes) - 1
            if selected_index < 0: selected_index = 0

            # Scroll Logic
            height, width = stdscr.getmaxyx()
            max_displayable = height - 1
            if selected_index < scroll_offset:
                scroll_offset = selected_index
            elif selected_index >= scroll_offset + max_displayable:
                scroll_offset = selected_index - max_displayable + 1
            
            draw_notes(stdscr, flat_notes, selected_index, scroll_offset, color_pair)
            
            current_note = flat_notes[selected_index]
            cursor_y_on_screen = selected_index - scroll_offset
            cursor_x = 2 
            if current_note.indent > 0:
                cursor_x += (current_note.indent * NOTE_INDENT_WIDTH) + 2
            cursor_x += len(current_note.content)

            if 0 <= cursor_y_on_screen < height and 0 <= cursor_x < width:
                try:
                    stdscr.move(cursor_y_on_screen, cursor_x)
                except curses.error: pass
            
            key = stdscr.getch()

            if key in [ord('q'), ord('Q')]: # Quit back to Matrix
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
                    selected_index = max(0, selected_index - 1)
            elif key == curses.KEY_RIGHT:
                if current_note.indent < 5:
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
        save_notes(notes, filename)

if __name__ == '__main__':
    curses.wrapper(main)