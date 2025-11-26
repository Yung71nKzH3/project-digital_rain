import curses
import random
import time
import psutil
import datetime
import math
import re
import subprocess
import os
import sys

# --- Configuration ---
MATRIX_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+-=[]{};:'\"\\|,./<>?`~"
ANIMATION_DELAY = 0.05
MIN_STREAK_LENGTH = 10
MAX_STREAK_LENGTH = 30
MIN_STREAK_SPEED = 1
MAX_STREAK_SPEED = 3
STREAK_DENSITY = 0.5

# Input effect variables
INPUT_EFFECT_DURATION = 1.0

# Output effect variables
OUTPUT_EFFECT_DURATION = 3.0
OUTPUT_MESSAGE = None
OUTPUT_FORMAT = "vertical" # Default output format

# New variables for on-demand stats and fade-out
STATS_DISPLAY_DURATION = 2.3 
stats_display_timer = 0

FADE_OUT_DURATION = 2.0
fade_out_active = False
fade_out_timer = 0
APP_TO_LAUNCH = None
NOTEPAD_FILENAME_TO_OPEN = None
SHOULD_EXIT = False

# Typing Test
TYPING_QUOTE = "the quick brown fox jumps over the lazy dog"
typing_test_active = False

# A single set of streaks for the whole screen to create a seamless effect
streaks = []
screen_height, screen_width = 0, 0
current_buffer = []
last_buffer = []

# --- User Input Buffer ---
input_buffer = ""

# --- Utility Functions ---
CONVERSION_FACTORS = {
    # Length & Weight
    'm': {'ft': 3.28084},
    'ft': {'m': 0.3048},
    'kg': {'lbs': 2.20462},
    'lbs': {'kg': 0.453592},
    'km': {'mi': 0.621371},
    'mi': {'km': 1.60934},
    # Temperature
    'c': {'f': lambda c: (c * 9/5) + 32},
    'f': {'c': lambda f: (f - 32) * 5/9},
    # Time
    'sec': {'min': 1/60, 'hr': 1/3600, 'd': 1/86400},
    'min': {'sec': 60, 'hr': 1/60, 'd': 1/1440},
    'hr': {'sec': 3600, 'min': 60, 'd': 1/24},
    'd': {'sec': 86400, 'min': 1440, 'hr': 24},
    # Data
    'b': {'kb': 1/1024, 'mb': 1/1048576, 'gb': 1/1073741824},
    'kb': {'b': 1024, 'mb': 1/1024, 'gb': 1/1048576},
    'mb': {'b': 1048576, 'kb': 1024, 'gb': 1/1024},
    'gb': {'b': 1073741824, 'kb': 1048576, 'mb': 1024}
}

LAUNCH_COMMANDS = {
    "vsc": "flatpak run com.visualstudio.code",
    "vivaldi": "flatpak run com.vivaldi.Vivaldi",
    "notepad": "gedit",
    "terminal": "gnome-terminal",
    "spotify": "flatpak run com.spotify.Client",
    "thonny": "thonny",
    "rstudio": "rstudio"
}

def convert_units(expression):
    match = re.fullmatch(r"(\d+(\.\d+)?)\s*([a-zA-Z]+)\s*to\s*([a-zA-Z]+)", expression.lower())
    
    if not match:
        return "Error: Invalid convert format", "vertical"
    
    try:
        value = float(match.group(1))
        unit1 = match.group(3)
        unit2 = match.group(4)
    except (ValueError, IndexError):
        return "Error: Invalid numbers or units", "vertical"
    
    if unit1 not in CONVERSION_FACTORS or unit2 not in CONVERSION_FACTORS[unit1]:
        return f"Error: Cannot convert from {unit1} to {unit2}", "vertical"

    factor = CONVERSION_FACTORS[unit1][unit2]
    if callable(factor):
        result = factor(value)
    else:
        result = value * factor

    return f"Result: {result:.2f} {unit2}", "vertical"

def calculate(expression):
    match = re.fullmatch(r"(\d+(\.\d+)?)\s*([-+*/])\s*(\d+(\.\d+)?)", expression)
    
    if not match:
        return "Error: Invalid format", "vertical"
    
    try:
        num1 = float(match.group(1))
        operator = match.group(3)
        num2 = float(match.group(4))
    except (ValueError, IndexError):
        return "Error: Invalid numbers", "vertical"

    if operator == '+':
        return f"Result: {num1 + num2:.2f}", "vertical"
    elif operator == '-':
        return f"Result: {num1 - num2:.2f}", "vertical"
    elif operator == '*':
        return f"Result: {num1 * num2:.2f}", "vertical"
    elif operator == '/':
        if num2 == 0:
            return "Error: Div by zero", "vertical"
        return f"Result: {num1 / num2:.2f}", "vertical"

    return "Error: Invalid operator", "vertical"

def list_notes():
    notes_files = [f for f in os.listdir('.') if f.endswith('.json')]
    if notes_files:
        return "Saved Notes:\n" + "\n".join(notes_files), "paragraph"
    else:
        return "No saved notes found.", "paragraph"

def shutdown_command(args):
    global fade_out_active, fade_out_timer, SHOULD_EXIT
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    SHOULD_EXIT = True
    return "Shutting down...", "vertical"

def notepad_command(args):
    global fade_out_active, fade_out_timer, APP_TO_LAUNCH, NOTEPAD_FILENAME_TO_OPEN
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    APP_TO_LAUNCH = "notepad.py"
    
    if args:
        # User provided a filename
        NOTEPAD_FILENAME_TO_OPEN = args.strip()
    else:
        # Auto-increment logic
        existing_numbers = []
        # Scan current directory for files like note_1.json, note_25.json
        for f in os.listdir('.'):
            if f.startswith("note_") and f.endswith(".json"):
                try:
                    # Extract the number between "note_" and ".json"
                    number_part = f[5:-5] 
                    existing_numbers.append(int(number_part))
                except ValueError:
                    continue
        
        if existing_numbers:
            next_num = max(existing_numbers) + 1
        else:
            next_num = 1
            
        NOTEPAD_FILENAME_TO_OPEN = f"note_{next_num}"

    return f"Launching Notepad...", "vertical"

def tetris_command(args):
    global fade_out_active, fade_out_timer, APP_TO_LAUNCH
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    APP_TO_LAUNCH = "tetris.py"
    return "Starting Tetris...", "vertical"

def open_command(args):
    global fade_out_active, fade_out_timer, APP_TO_LAUNCH
    program_name = args.strip().lower()
    if program_name not in LAUNCH_COMMANDS:
        return f"Error: '{program_name}' is not a recognized application.", "vertical"
    
    fade_out_active = True
    fade_out_timer = time.time() + FADE_OUT_DURATION
    APP_TO_LAUNCH = program_name
    return f"Opening {program_name}...", "vertical"

# A dictionary to route commands to their functions
COMMANDS = {
    "calc": lambda args: calculate(args),
    "convert": lambda args: convert_units(args),
    "stats": lambda args: (None, None),
    "notepad": lambda args: notepad_command(args),
    "notes": lambda args: list_notes(),
    "shutdown": lambda args: shutdown_command(args),
    "tetris": lambda args: tetris_command(args),
    "open": lambda args: open_command(args)
}

def command_processor(command_string):
    global stats_display_timer, typing_test_active, fade_out_active, fade_out_timer, APP_TO_LAUNCH
    parts = command_string.split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "stats":
        stats_display_timer = time.time() + STATS_DISPLAY_DURATION
        return "Displaying system stats...", "vertical"

    if command in COMMANDS:
        return COMMANDS[command](args)
    else:
        return f"Error: '{command}' is not a valid command", "vertical"

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
    half_height, half_width = height // 2, width // 2

    for y in range(height):
        for x in range(width):
            current_buffer[y][x] = (' ', 0)

    current_time = time.time()
    if fade_out_active and time.time() < fade_out_timer:
        remaining_time = fade_out_timer - current_time
        fade_factor = remaining_time / FADE_OUT_DURATION
    else:
        fade_factor = 1.0

    new_streaks = []
    for streak in streaks:
        if random.random() < fade_factor:
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
    
    for key, messages in messages_data.items():
        if messages:
            y_quad, x_quad = key
            pane_height = half_height if y_quad == 0 else height - half_height
            pane_width = half_width if x_quad == 0 else width - half_width

            if key == (1, 0) and OUTPUT_FORMAT == "vertical":
                message_chars = list(messages[0]) if isinstance(messages[0], str) else messages[0]
                msg_len = len(message_chars)
                start_y_pane = (pane_height - msg_len) // 2
                start_x_offset = 0
                start_y_offset = half_height
                
                for i, char in enumerate(message_chars):
                    msg_x = (pane_width - 1) // 2 + start_x_offset
                    msg_y = start_y_pane + i + start_y_offset
                    if 0 <= msg_y < height and 0 <= msg_x < width:
                        current_buffer[msg_y][msg_x] = (char, color_pair)
            
            elif key == (1, 0) and OUTPUT_FORMAT == "paragraph":
                message_lines = messages[0].split('\n') if isinstance(messages[0], str) and '\n' in messages[0] else messages
                msg_len = len(message_lines)
                start_y_pane = (pane_height - msg_len) // 2
                start_x_offset = 0
                start_y_offset = half_height
                
                for i, msg in enumerate(message_lines):
                    msg_x = (pane_width - len(msg)) // 2 + start_x_offset
                    msg_y = start_y_pane + i + start_y_offset
                    if 0 <= msg_y < height and 0 <= msg_x < width:
                        for j, char in enumerate(msg):
                            current_buffer[msg_y][msg_x + j] = (char, color_pair)
            else:
                msg_len = len(messages)
                start_y_pane = (pane_height - msg_len) // 2
                start_x_offset = half_width if x_quad == 1 else 0
                start_y_offset = half_height if y_quad == 1 else 0

                for i, msg in enumerate(messages):
                    for j, char in enumerate(msg):
                        msg_x = (pane_width - len(msg)) // 2 + start_x_offset + j
                        msg_y = start_y_pane + i + start_y_offset
                        if 0 <= msg_y < height and 0 <= msg_x < width:
                            current_buffer[msg_y][msg_x] = (char, color_pair)


def refresh_dirty_pixels(stdscr):
    for y in range(screen_height):
        for x in range(screen_width):
            if current_buffer[y][x] != last_buffer[y][x]:
                char, color = current_buffer[y][x]
                try:
                    stdscr.addstr(y, x, char, color)
                except curses.error:
                    pass

def main(stdscr):
    global streaks, screen_height, screen_width, current_buffer, last_buffer, input_buffer, OUTPUT_MESSAGE, OUTPUT_FORMAT, stats_display_timer, fade_out_active, fade_out_timer, APP_TO_LAUNCH, NOTEPAD_FILENAME_TO_OPEN, SHOULD_EXIT, typing_test_active
    
    stdscr.clear()
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_BLACK)
        color_pair = curses.color_pair(1)
    else:
        color_pair = 0

    screen_height, screen_width = stdscr.getmaxyx()
    streaks = create_streaks(screen_width, screen_height)
    current_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
    last_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
    
    output_message_timer = 0
    
    while True:
        if fade_out_active and time.time() >= fade_out_timer:
            if SHOULD_EXIT:
                break

            curses.endwin()

            try:
                # Prepare the command to run the script
                command_list = []
                
                # Check for the desktop environment to set the correct flags
                is_i3 = os.environ.get('DESKTOP_SESSION') == 'i3'
                
                # The fullscreen flag is only added for GNOME (not i3)
                fullscreen_flag = "--full-screen" if not is_i3 else ""
                
                # Get directory of current script to find notepad/tetris relative to it
                base_dir = os.path.dirname(os.path.abspath(__file__))

                if APP_TO_LAUNCH == "notepad.py":
                    script_path = os.path.join(base_dir, "notepad.py")
                    # Launch notepad.py in a NEW terminal
                    command = ["gnome-terminal", fullscreen_flag, "--", "python3", script_path]
                    command_list = [c for c in command if c] # This removes any empty strings
                    if NOTEPAD_FILENAME_TO_OPEN:
                        command_list.append(NOTEPAD_FILENAME_TO_OPEN)

                elif APP_TO_LAUNCH == "tetris.py":
                    script_path = os.path.join(base_dir, "tetris.py")
                    # Launch tetris.py in a NEW terminal
                    command = ["gnome-terminal", fullscreen_flag, "--", "python3", script_path]
                    command_list = [c for c in command if c]

                elif APP_TO_LAUNCH in LAUNCH_COMMANDS:
                    command = LAUNCH_COMMANDS.get(APP_TO_LAUNCH)
                    command_list = command.split()

                if command_list:
                    subprocess.run(command_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                OUTPUT_MESSAGE = None
            except Exception as e:
                OUTPUT_MESSAGE = f"Error launching {APP_TO_LAUNCH}: {e}"
                OUTPUT_FORMAT = "vertical"
                output_message_timer = time.time() + OUTPUT_EFFECT_DURATION

            # Re-initialize the curses screen state
            stdscr.clear()
            stdscr.refresh()

            fade_out_active = False
            APP_TO_LAUNCH = None
            NOTEPAD_FILENAME_TO_OPEN = None
            
            continue

        new_height, new_width = stdscr.getmaxyx()
        if (new_height, new_width) != (screen_height, new_width):
            screen_height, screen_width = new_height, new_width
            streaks = create_streaks(screen_width, screen_height)
            current_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
            last_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
            
        key = stdscr.getch()
        if key != -1:
            if key in [ord('q'), ord('Q')]:
                break
            elif key == curses.KEY_ENTER or key == ord('\n'):
                OUTPUT_MESSAGE, OUTPUT_FORMAT = command_processor(input_buffer.strip())
                output_message_timer = time.time() + OUTPUT_EFFECT_DURATION
                input_buffer = ""
            elif key == curses.KEY_BACKSPACE or key == ord('\b'):
                input_buffer = input_buffer[:-1]
            elif 32 <= key < 127:
                input_buffer += chr(key)
        
        if time.time() > output_message_timer:
            OUTPUT_MESSAGE = None
            OUTPUT_FORMAT = "vertical"

        cpu_usage = psutil.cpu_percent(interval=None)
        mem_usage = psutil.virtual_memory().percent
        current_time = datetime.datetime.now()

        messages_data = {
            (0, 0): [input_buffer] if input_buffer else None,
            (1, 0): [OUTPUT_MESSAGE] if OUTPUT_MESSAGE else None
        }

        if time.time() < stats_display_timer:
            messages_data[(0, 1)] = [
                f"CPU: {cpu_usage:0>2.0f}%",
                f"MEM: {mem_usage:0>2.0f}%"
            ]
            messages_data[(1, 1)] = [
                f"DAY: {current_time.strftime('%A')}",
                f"DATE: {current_time.strftime('%d/%m/%Y')}",
                f"TIME: {current_time.strftime('%H:%M:%S')}"
            ]
            
        last_buffer = [row[:] for row in current_buffer]

        draw_seamless_rain_to_buffer(messages_data, color_pair)
        
        refresh_dirty_pixels(stdscr)

        stdscr.refresh()
        
        time.sleep(ANIMATION_DELAY)

if __name__ == '__main__':
    curses.wrapper(main)