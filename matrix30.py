import curses
import random
import time
import psutil
import datetime
import math
import re
import subprocess
import os

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
STATS_DISPLAY_DURATION = 5.0
stats_display_timer = 0

FADE_OUT_DURATION = 2.0
fade_out_active = False
fade_out_timer = 0
APP_TO_LAUNCH = None
NOTEPAD_FILENAME_TO_OPEN = None
SHOULD_EXIT = False

# Typing Test
TYPING_QUOTE = "The Matrix is a system, Neo. That system is our enemy."
typing_test_active = False

# A single set of streaks for the whole screen to create a seamless effect
streaks = []
screen_height, screen_width = 0, 0
current_buffer = []
last_buffer = []

# --- User Input Buffer ---
input_buffer = ""

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
    APP_TO_LAUNCH = "notepad"
    if args:
        NOTEPAD_FILENAME_TO_OPEN = args.strip()
        return f"Launching Notepad: {args}", "vertical"
    else:
        current_time = datetime.datetime.now()
        filename = current_time.strftime("%d%m%y%H%M")
        NOTEPAD_FILENAME_TO_OPEN = filename
        return f"Launching New Notepad: {filename}", "vertical"

# A dictionary to route commands to their functions
COMMANDS = {
    "calc": lambda args: calculate(args),
    "convert": lambda args: convert_units(args),
    "stats": lambda args: (None, None),
    "notepad": lambda args: notepad_command(args),
    "notes": lambda args: list_notes(),
    "shutdown": lambda args: shutdown_command(args),
    "type": lambda args: (None, None)
}

def command_processor(command_string):
    global stats_display_timer, typing_test_active, fade_out_active, fade_out_timer, APP_TO_LAUNCH
    parts = command_string.split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    if command == "stats":
        stats_display_timer = time.time() + STATS_DISPLAY_DURATION
        return "Displaying system stats...", "vertical"
    elif command == "type":
        fade_out_active = True
        fade_out_timer = time.time() + FADE_OUT_DURATION
        APP_TO_LAUNCH = "type"
        return "Starting typing test...", "vertical"

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
    fade_factor = 1.0
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

def typing_test_loop(stdscr, color_pair):
    global OUTPUT_MESSAGE, OUTPUT_FORMAT, OUTPUT_EFFECT_DURATION, animation_delay
    
    stdscr.nodelay(True)
    curses.curs_set(1)
    stdscr.clear()

    quote_to_type = TYPING_QUOTE
    typed_text = ""
    start_time = None
    
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        
        quote_y = height // 2 - 2
        input_y = height // 2
        
        stdscr.addstr(quote_y, (width - len(quote_to_type)) // 2, quote_to_type, color_pair)
        stdscr.addstr(input_y, (width - len(quote_to_type)) // 2, typed_text, color_pair)
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key != -1:
            if not start_time:
                start_time = time.time()
                
            if key == curses.KEY_ENTER or key == ord('\n'):
                if typed_text.strip() == quote_to_type:
                    end_time = time.time()
                    time_taken = end_time - start_time if start_time else 0
                    words_per_minute = (len(typed_text.split()) / time_taken) * 60 if time_taken > 0 else 0
                    
                    OUTPUT_MESSAGE = f"WPM: {words_per_minute:.2f}\nAccuracy: 100.00%"
                else:
                    correct_chars = 0
                    for i, char in enumerate(typed_text):
                        if i < len(quote_to_type) and char == quote_to_type[i]:
                            correct_chars += 1
                    accuracy = (correct_chars / len(quote_to_type)) * 100 if len(quote_to_type) > 0 else 0
                    
                    time_taken = time.time() - start_time if start_time else 0
                    words_per_minute = (len(typed_text.split()) / time_taken) * 60 if time_taken > 0 else 0
                    
                    OUTPUT_MESSAGE = f"WPM: {words_per_minute:.2f}\nAccuracy: {accuracy:.2f}%"

                OUTPUT_FORMAT = "paragraph"
                return OUTPUT_MESSAGE, OUTPUT_FORMAT

            elif key == curses.KEY_BACKSPACE or key == ord('\b'):
                typed_text = typed_text[:-1]
            elif 32 <= key < 127:
                if len(typed_text) < len(quote_to_type):
                    typed_text += chr(key)
        
        time.sleep(ANIMATION_DELAY)
    return None, None

def main(stdscr):
    global streaks, screen_height, screen_width, current_buffer, last_buffer, input_buffer, OUTPUT_MESSAGE, OUTPUT_FORMAT, stats_display_timer, fade_out_active, fade_out_timer, APP_TO_LAUNCH, SHOULD_EXIT, typing_test_active
    
    stdscr.clear()
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN)
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
            
            if APP_TO_LAUNCH == "type":
                OUTPUT_MESSAGE, OUTPUT_FORMAT = typing_test_loop(stdscr, color_pair)
                output_message_timer = time.time() + OUTPUT_EFFECT_DURATION
                typing_test_active = False
                fade_out_active = False
                APP_TO_LAUNCH = None
                stdscr.clear()
                continue
            
            command_to_run = ["python"]
            if APP_TO_LAUNCH == "notepad":
                command_to_run.append("notepad.py")
                if NOTEPAD_FILENAME_TO_OPEN:
                    command_to_run.append(NOTEPAD_FILENAME_TO_OPEN)
            elif APP_TO_LAUNCH == "tetris":
                command_to_run.append("tetris.py")
            
            subprocess.run(command_to_run)
                
            fade_out_active = False
            fade_out_timer = 0
            APP_TO_LAUNCH = None
            stdscr.clear()
            
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
                f"MEM: {mem_usage:0>2.0f}%",
                f"DAY: {current_time.strftime('%A')}"
            ]
            messages_data[(1, 1)] = [
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

