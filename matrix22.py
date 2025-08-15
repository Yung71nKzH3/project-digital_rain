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

# New variables for on-demand stats and fade-out
STATS_DISPLAY_DURATION = 5.0
stats_display_timer = 0

FADE_OUT_DURATION = 2.0
fade_out_active = False
fade_out_timer = 0

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
        return "Error: Invalid format"
    
    try:
        num1 = float(match.group(1))
        operator = match.group(3)
        num2 = float(match.group(4))
    except (ValueError, IndexError):
        return "Error: Invalid numbers"

    if operator == '+':
        return f"Result: {num1 + num2:.2f}"
    elif operator == '-':
        return f"Result: {num1 - num2:.2f}"
    elif operator == '*':
        return f"Result: {num1 * num2:.2f}"
    elif operator == '/':
        if num2 == 0:
            return "Error: Div by zero"
        return f"Result: {num1 / num2:.2f}"

    return "Error: Invalid operator"

def command_processor(command_string):
    global fade_out_active, fade_out_timer, stats_display_timer, OUTPUT_MESSAGE

    parts = command_string.split(" ", 1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    if command == "calc":
        return calculate(args)
    elif command == "stats":
        stats_display_timer = time.time() + STATS_DISPLAY_DURATION
        return "Displaying system stats..."
    elif command == "notepad":
        fade_out_active = True
        fade_out_timer = time.time() + FADE_OUT_DURATION
        return f"Launching Notepad: {args}" if args else "Launching New Notepad"
    elif command == "notes":
        notes_files = [f for f in os.listdir('.') if f.endswith('.json')]
        if notes_files:
            return "Saved Notes:\n" + "\n".join(notes_files)
        else:
            return "No saved notes found."
    return f"Error: '{command}' is not a valid command"

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
    if fade_out_active and current_time < fade_out_timer:
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

            if key == (1, 0):
                if isinstance(messages[0], str) and '\n' in messages[0]:
                    message_lines = messages[0].split('\n')
                else:
                    message_lines = messages
                    
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
    height, width = screen_height, screen_width
    for y in range(height):
        for x in range(width):
            if current_buffer[y][x] != last_buffer[y][x]:
                char, color = current_buffer[y][x]
                try:
                    stdscr.addstr(y, x, char, color)
                except curses.error:
                    pass

def main(stdscr):
    global streaks, screen_height, screen_width, current_buffer, last_buffer, input_buffer, OUTPUT_MESSAGE, stats_display_timer, fade_out_active, fade_out_timer
    
    stdscr.clear()
    curses.curs_set(1)
    stdscr.nodelay(True)
    stdscr.timeout(0)

    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        color_pair = curses.color_pair(1)
    else:
        color_pair = 0

    screen_height, screen_width = stdscr.getmaxyx()
    streaks = create_streaks(screen_width, screen_height)
    current_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
    last_buffer = [[('', 0) for _ in range(screen_width)] for _ in range(screen_height)]
    
    output_message_timer = 0
    
    while True:
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
                result = command_processor(input_buffer.strip())
                OUTPUT_MESSAGE = result
                output_message_timer = time.time() + OUTPUT_EFFECT_DURATION
                input_buffer = ""
            elif key == curses.KEY_BACKSPACE or key == ord('\b'):
                input_buffer = input_buffer[:-1]
            elif 32 <= key < 127:
                input_buffer += chr(key)
        
        if time.time() > output_message_timer:
            OUTPUT_MESSAGE = None

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
        
        if fade_out_active and time.time() > fade_out_timer:
            filename_to_open = input_buffer.split(" ", 1)[1] if " " in input_buffer else None
            if filename_to_open:
                subprocess.run(["python", "notepad.py", filename_to_open])
            else:
                subprocess.run(["python", "notepad.py"])
                
            fade_out_active = False
            fade_out_timer = 0
            stdscr.clear()

        time.sleep(ANIMATION_DELAY)

if __name__ == '__main__':
    curses.wrapper(main)
