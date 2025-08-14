import curses
import random
import time
import psutil
import datetime
import math

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

# A single set of streaks for the whole screen to create a seamless effect
streaks = []
screen_height, screen_width = 0, 0
current_buffer = []
last_buffer = []


def create_streaks(width, height):
    """Creates a single list of streaks for the entire screen."""
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

def draw_seamless_rain_to_buffer(input_char_effect, messages_data, color_pair):
    """
    Draws a single, seamless digital rain animation to a memory buffer.
    """
    height, width = screen_height, screen_width
    half_height, half_width = height // 2, width // 2

    # Fill buffer with empty spaces
    for y in range(height):
        for x in range(width):
            current_buffer[y][x] = (' ', 0) # (character, color_pair)

    # Draw the rain to the buffer
    for streak in streaks:
        for i in range(streak['length']):
            y_pos = streak['y'] + i
            x_pos = streak['x']
            
            if 0 <= y_pos < height and 0 <= x_pos < width:
                # Top-left quadrant has the input effect
                if y_pos < half_height and x_pos < half_width and input_char_effect:
                    char_to_draw = input_char_effect
                else:
                    char_to_draw = streak['char_set'][i]
                
                current_buffer[y_pos][x_pos] = (char_to_draw, color_pair)

        # Update streak positions
        streak['y'] += streak['speed']
        
        # Reset streak if it goes off screen
        if streak['y'] > height:
            streak['y'] = random.randint(-height, 0)
            streak['length'] = random.randint(MIN_STREAK_LENGTH, MAX_STREAK_LENGTH)
            streak['speed'] = random.randint(MIN_STREAK_SPEED, MAX_STREAK_SPEED)
            streak['char_set'] = [random.choice(MATRIX_CHARS) for _ in range(streak['length'])]
    
    # Draw permanent text over the rain in the buffer
    for key, messages in messages_data.items():
        if messages:
            y_quad, x_quad = key
            
            pane_height = half_height if y_quad == 0 else height - half_height
            pane_width = half_width if x_quad == 0 else width - half_width

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
    """
    Compares the current buffer to the last buffer and only redraws changed pixels.
    """
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
    global streaks, screen_height, screen_width, current_buffer, last_buffer
    
    stdscr.clear()
    curses.curs_set(0)
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
    current_buffer = [['' for _ in range(screen_width)] for _ in range(screen_height)]
    last_buffer = [['' for _ in range(screen_width)] for _ in range(screen_height)]
    
    input_effect_timer = 0
    output_message_timer = 0
    input_effect_char = None
    output_message = None

    while True:
        # Re-initialize streaks on resize
        new_height, new_width = stdscr.getmaxyx()
        if (new_height, new_width) != (screen_height, new_width):
            screen_height, screen_width = new_height, new_width
            streaks = create_streaks(screen_width, screen_height)
            current_buffer = [['' for _ in range(screen_width)] for _ in range(screen_height)]
            last_buffer = [['' for _ in range(screen_width)] for _ in range(screen_height)]
            
        key = stdscr.getch()
        if key != -1:
            if key in [ord('q'), ord('Q')]:
                break
            try:
                pressed_char = chr(key)
                input_effect_char = pressed_char
                input_effect_timer = time.time() + INPUT_EFFECT_DURATION
                if pressed_char.isdigit():
                    output_message = f"Math: {pressed_char} * 2 = {int(pressed_char) * 2}"
                    output_message_timer = time.time() + OUTPUT_EFFECT_DURATION
            except ValueError:
                pass

        if time.time() > input_effect_timer:
            input_effect_char = None
        if time.time() > output_message_timer:
            output_message = None

        cpu_usage = psutil.cpu_percent(interval=None)
        mem_usage = psutil.virtual_memory().percent
        current_time = datetime.datetime.now()

        messages_data = {
            (1, 0): [output_message] if output_message else None,
            (0, 1): [
                f"CPU: {cpu_usage:0>2.0f}%",
                f"MEM: {mem_usage:0>2.0f}%"
            ],
            (1, 1): [
                current_time.strftime("%d/%m/%Y"),
                current_time.strftime("%H:%M:%S")
            ]
        }
        
        # 1. Update the last buffer with the current frame
        last_buffer = [row[:] for row in current_buffer]

        # 2. Draw everything to the current buffer
        draw_seamless_rain_to_buffer(input_effect_char, messages_data, color_pair)
        
        # 3. Compare and refresh only the "dirty" pixels
        refresh_dirty_pixels(stdscr)

        stdscr.refresh()
        
        time.sleep(ANIMATION_DELAY)

if __name__ == '__main__':
    curses.wrapper(main)
