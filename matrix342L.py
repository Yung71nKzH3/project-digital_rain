import curses
import random
import time
import psutil
import datetime
import math
import re
import os
import sys

# Import our Integrated Apps
# Note: Ensure tetris.py and notepad.py are in the same folder!
try:
    import tetris
    import notepad
except ImportError:
    pass # Will handle gracefully if missing

# --- Configuration ---
MATRIX_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+-=[]{};:'\"\\|,./<>?`~"
ANIMATION_DELAY = 0.05
MIN_STREAK_LENGTH = 10
MAX_STREAK_LENGTH = 30
MIN_STREAK_SPEED = 1
MAX_STREAK_SPEED = 3
STREAK_DENSITY = 0.5

# Input/Output variables
OUTPUT_EFFECT_DURATION = 3.0
OUTPUT_MESSAGE = None
OUTPUT_FORMAT = "vertical"
STATS_DISPLAY_DURATION = 2.3 
stats_display_timer = 0
FADE_OUT_DURATION = 1.0 # Faster fade for internal transitions
fade_out_active = False
fade_out_timer = 0
APP_TO_LAUNCH_INTERNAL = None # Stores the function to call
NOTEPAD_FILENAME = None
SHOULD_EXIT = False

# Typing Test Data
TYPING_QUOTES = [
    "The Matrix is everywhere. It is all around us.",
    "Wake up, Neo... The Matrix has you.",
    "I know kung fu.",
    "There is no spoon.",
    "Follow the white rabbit.",
    "Ignorance is bliss.",
    "Never send a human to do a machine's job.",
    "Code is poetry written in logic."
]

streaks = []
screen_height, screen_width = 0, 0
current_buffer = []
last_buffer = []
input_buffer = ""

# --- Helper Functions ---
CONVERSION_FACTORS = {
    # Length
    'm': {'ft': 3.28084}, 'ft': {'m': 0.3048},
    'km': {'mi': 0.621371}, 'mi': {'km': 1.60934},
    # Weight
    'kg': {'lbs': 2.20462}, 'lbs': {'kg': 0.453592},
    # Temperature (using lambdas for non-linear)
    'c': {'f': lambda c: (c * 9/5) + 32}, 'f': {'c': lambda f: (f - 32) * 5/9},
    # Data Storage
    'b': {'kb': 1/1024, 'mb': 1/1048576, 'gb': 1/1073741824},
    'kb': {'b': 1024, 'mb': 1/1024, 'gb': 1/1048576},
    'mb': {'b': 1048576, 'kb': 1024, 'gb': 1/1024},
    'gb': {'b': 1073741824, 'kb': 1048576, 'mb': 1024}
}

def convert_units(expression):
    # Regex to capture number, source unit, "to", target unit
    match = re.fullmatch(r"(\d+(\.\d+)?)\s*([a-zA-Z]+)\s*to\s*([a-zA-Z]+)", expression.lower())
    if not match: return "Error: Invalid convert format", "vertical"
    try:
        value = float(match.group(1))
        unit1 = match.group(3)
        unit2 = match.group(4)
    except: return "Error: Invalid input", "vertical"
    
    if unit1 not in CONVERSION_FACTORS or unit2 not in CONVERSION_FACTORS[unit1]:
        return f"Error: Cannot convert {unit1} to {unit2}", "vertical"

    factor = CONVERSION_FACTORS[unit1][unit2]
    result = factor(value) if callable(factor) else value * factor
    
    # Format based on magnitude
    if result < 0.01:
        return f"Result: {result:.6f} {unit2}", "vertical"
    else:
        return f"Result: {result:.2f} {unit2}", "vertical"

def calculate(expression):
    try:
        # Simple safe eval wrapper
        allowed = set("0123456789.+-*/ ")
        if not set(expression).issubset(allowed): return "Error: Invalid chars", "vertical"
        return f"Result: {eval(expression):.2f}", "vertical"
    except:
        return "Error: Calc failed", "vertical"

def list_notes():
    notes_files = [f for f in os.listdir('.') if f.endswith('.json')]
    if notes_files:
        return "Saved Notes:\n" + "\n".join(notes_files), "paragraph"
    else:
        return "No saved notes found.", "paragraph"

# --- TYPING TEST FEATURE ---
def run_typing_test(stdscr):
    curses.curs_set(1)
    stdscr.nodelay(False) # Blocking input
    target_text = random.choice(TYPING_QUOTES)
    user_text = ""
    start_time = None
    
    # Colors: 1=Green, 2=Black, 3=Red(Error), 4=White(Text)
    if curses.has_colors():
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
    
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        
        # Header
        header = "--- TYPING CONSTRUCT ---"
        stdscr.addstr(h//2 - 4, (w-len(header))//2, header, curses.color_pair(1) | curses.A_BOLD)
        
        # Target Text
        stdscr.addstr(h//2 - 2, (w-len(target_text))//2, target_text, curses.color_pair(4))
        
        # User Text (with coloring)
        start_x = (w - len(target_text)) // 2
        for i, char in enumerate(user_text):
            if i < len(target_text) and char == target_text[i]:
                color = curses.color_pair(1) # Green for correct
            else:
                color = curses.color_pair(3) # Red for wrong
            stdscr.addstr(h//2, start_x + i, char, color)
            
        # Stats
        if start_time and len(user_text) > 0:
            elapsed = time.time() - start_time
            wpm = (len(user_text) / 5) / (elapsed / 60) if elapsed > 0 else 0
            stats = f"WPM: {wpm:.1f} | Chars: {len(user_text)}/{len(target_text)}"
            stdscr.addstr(h//2 + 2, (w-len(stats))//2, stats, curses.color_pair(4))

        stdscr.refresh()
        
        # Input Logic
        key = stdscr.getch()
        
        if start_time is None:
            start_time = time.time()
            
        if key == 27: # ESC to quit
            break
        elif key == curses.KEY_BACKSPACE or key == 127 or key == ord('\b'):
            user_text = user_text[:-1]
        elif key == ord('\n') or key == curses.KEY_ENTER:
            if user_text == target_text:
                break # Success
        elif 32 <= key <= 126:
            if len(user_text) < len(target_text):
                user_text += chr(key)
                # Check for instant finish
                if user_text == target_text:
                    elapsed = time.time() - start_time
                    wpm = (len(user_text) / 5) / (elapsed / 60)
                    stdscr.addstr(h//2 + 4, (w-20)//2, "CONSTRUCT COMPLETE", curses.color_pair(1) | curses.A_BLINK)
                    stdscr.refresh()
                    time.sleep(2)
                    break

# --- COMMANDS ---

def shutdown_command(args):
    global fade_out_active, fade_out_timer, SHOULD_EXIT
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    SHOULD_EXIT = True
    return "Shutting down...", "vertical"

def notepad_command(args):
    global fade_out_active, fade_out_timer, APP_TO_LAUNCH_INTERNAL, NOTEPAD_FILENAME
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    
    if args:
        NOTEPAD_FILENAME = args.strip()
    else:
        # Auto-increment logic
        existing_numbers = []
        for f in os.listdir('.'):
            if f.startswith("note_") and f.endswith(".json"):
                try:
                    existing_numbers.append(int(f[5:-5]))
                except ValueError: continue
        next_num = (max(existing_numbers) + 1) if existing_numbers else 1
        NOTEPAD_FILENAME = f"note_{next_num}"
    
    APP_TO_LAUNCH_INTERNAL = notepad.main
    return "Initializing Notepad...", "vertical"

def tetris_command(args):
    global fade_out_active, fade_out_timer, APP_TO_LAUNCH_INTERNAL
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    APP_TO_LAUNCH_INTERNAL = tetris.main
    return "Initializing Tetris...", "vertical"

def type_command(args):
    global fade_out_active, fade_out_timer, APP_TO_LAUNCH_INTERNAL
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    APP_TO_LAUNCH_INTERNAL = run_typing_test
    return "Loading Construct...", "vertical"

COMMANDS = {
    "calc": lambda args: calculate(args),
    "convert": lambda args: convert_units(args),
    "stats": lambda args: (None, None),
    "notepad": lambda args: notepad_command(args),
    "notes": lambda args: list_notes(),
    "shutdown": lambda args: shutdown_command(args),
    "tetris": lambda args: tetris_command(args),
    "type": lambda args: type_command(args)
}

def command_processor(command_string):
    global stats_display_timer
    parts = command_string.split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "stats":
        stats_display_timer = time.time() + STATS_DISPLAY_DURATION
        return "Displaying system stats...", "vertical"

    if command in COMMANDS:
        return COMMANDS[command](args)
    else:
        return f"Error: '{command}' invalid", "vertical"

# --- MATRIX ENGINE ---

def create_streaks(width, height):
    streaks = []
    num_streaks = int(width * STREAK_DENSITY)
    for _ in range(num_streaks):
        x = random.randint(0, width - 1)
        y = random.randint(-height, 0)
        length = random.randint(MIN_STREAK_LENGTH, MAX_STREAK_LENGTH)
        speed = random.randint(MIN_STREAK_SPEED, MAX_STREAK_SPEED)
        char_set = [random.choice(MATRIX_CHARS) for _ in range(length)]
        streaks.append({'x': x, 'y': y, 'length': length, 'speed': speed, 'char_set': char_set})
    return streaks

def draw_seamless_rain_to_buffer(messages_data, color_pair):
    height, width = screen_height, screen_width
    
    # Clear Buffer
    for y in range(height):
        for x in range(width):
            current_buffer[y][x] = (' ', 0)

    # Fade Effect logic
    current_time = time.time()
    fade_factor = 1.0
    if fade_out_active and time.time() < fade_out_timer:
        remaining_time = fade_out_timer - current_time
        fade_factor = remaining_time / FADE_OUT_DURATION

    # Rain Logic
    new_streaks = []
    for streak in streaks:
        if random.random() < fade_factor: # Fade out by reducing chance of drawing
            for i in range(streak['length']):
                y_pos = streak['y'] + i
                x_pos = streak['x']
                if 0 <= y_pos < height and 0 <= x_pos < width:
                    char_to_draw = streak['char_set'][i]
                    current_buffer[y_pos][x_pos] = (char_to_draw, color_pair)

        streak['y'] += streak['speed']
        if streak['y'] > height:
            streak['y'] = random.randint(-height, 0)
            streak['length'] = random.randint(MIN_STREAK_LENGTH, MAX_STREAK_LENGTH)
            streak['speed'] = random.randint(MIN_STREAK_SPEED, MAX_STREAK_SPEED)
            streak['char_set'] = [random.choice(MATRIX_CHARS) for _ in range(streak['length'])]
        new_streaks.append(streak)
    streaks.clear()
    streaks.extend(new_streaks)
    
    # UI Overlays (Command output, input box)
    for key, messages in messages_data.items():
        if not messages: continue
        y_quad, x_quad = key
        pane_h = height // 2 if y_quad == 0 else height - (height // 2)
        pane_w = width // 2 if x_quad == 0 else width - (width // 2)
        start_y = 0 if y_quad == 0 else height // 2
        start_x = 0 if x_quad == 0 else width // 2

        # Simple centered text rendering
        content = messages[0] if isinstance(messages, list) else messages
        lines = content.split('\n') if isinstance(content, str) else content
        if not isinstance(lines, list): lines = [str(lines)]
        
        msg_start_y = start_y + (pane_h - len(lines)) // 2
        
        for i, line in enumerate(lines):
            msg_x = start_x + (pane_w - len(line)) // 2
            msg_y = msg_start_y + i
            if 0 <= msg_y < height:
                for j, char in enumerate(line):
                    if 0 <= msg_x + j < width:
                        current_buffer[msg_y][msg_x+j] = (char, color_pair)

def main(stdscr):
    global streaks, screen_height, screen_width, current_buffer, last_buffer
    global input_buffer, OUTPUT_MESSAGE, OUTPUT_FORMAT
    global stats_display_timer, fade_out_active, APP_TO_LAUNCH_INTERNAL, NOTEPAD_FILENAME
    
    # Initial Setup
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.timeout(0)
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        color_pair = curses.color_pair(1)
    else: color_pair = 0

    screen_height, screen_width = stdscr.getmaxyx()
    streaks = create_streaks(screen_width, screen_height)
    current_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
    last_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
    
    output_message_timer = 0
    
    while True:
        # --- APP LAUNCHER LOGIC ---
        if fade_out_active and time.time() >= fade_out_timer:
            if SHOULD_EXIT: break
            
            # Execute the Internal App
            if APP_TO_LAUNCH_INTERNAL:
                try:
                    if APP_TO_LAUNCH_INTERNAL == notepad.main:
                        notepad.main(stdscr, NOTEPAD_FILENAME)
                    else:
                        APP_TO_LAUNCH_INTERNAL(stdscr)
                except Exception as e:
                    OUTPUT_MESSAGE = f"Sys Error: {e}"
                    output_message_timer = time.time() + 3.0
                
                # Restore Matrix State after app returns
                stdscr.clear()
                stdscr.nodelay(True)
                stdscr.timeout(0)
                curses.curs_set(1)
                
            # Reset State
            fade_out_active = False
            APP_TO_LAUNCH_INTERNAL = None
            OUTPUT_MESSAGE = None
            
            # Re-init buffer to avoid artifacts
            last_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]

        # --- RESIZE HANDLING ---
        new_height, new_width = stdscr.getmaxyx()
        if (new_height, new_width) != (screen_height, new_width):
            screen_height, screen_width = new_height, new_width
            streaks = create_streaks(screen_width, screen_height)
            current_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
            last_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
            stdscr.clear()

        # --- INPUT HANDLING ---
        try:
            key = stdscr.getch()
        except: key = -1
        
        if key != -1:
            if key == 27: # ESC to clear input
                input_buffer = ""
            elif key == curses.KEY_ENTER or key == ord('\n'):
                OUTPUT_MESSAGE, OUTPUT_FORMAT = command_processor(input_buffer.strip())
                output_message_timer = time.time() + OUTPUT_EFFECT_DURATION
                input_buffer = ""
            elif key == curses.KEY_BACKSPACE or key == 127 or key == ord('\b'):
                input_buffer = input_buffer[:-1]
            elif 32 <= key < 127:
                input_buffer += chr(key)

        if time.time() > output_message_timer:
            OUTPUT_MESSAGE = None

        # --- RENDER FRAME ---
        messages_data = {
            (0, 0): [input_buffer] if input_buffer else None,
            (1, 0): [OUTPUT_MESSAGE] if OUTPUT_MESSAGE else None
        }
        
        # Stats Overlay
        if time.time() < stats_display_timer:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            now = datetime.datetime.now()
            messages_data[(0, 1)] = [f"CPU: {cpu:.0f}%", f"MEM: {mem:.0f}%"]
            messages_data[(1, 1)] = [now.strftime('%H:%M:%S')]

        draw_seamless_rain_to_buffer(messages_data, color_pair)
        
        # Optimize Drawing (Only update changed pixels)
        for y in range(screen_height):
            for x in range(screen_width):
                if current_buffer[y][x] != last_buffer[y][x]:
                    char, color = current_buffer[y][x]
                    try: stdscr.addstr(y, x, char, color)
                    except: pass
        
        last_buffer = [row[:] for row in current_buffer]
        stdscr.refresh()
        time.sleep(ANIMATION_DELAY)

if __name__ == '__main__':
    curses.wrapper(main)