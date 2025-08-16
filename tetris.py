import curses
import random
import time
import sys
import os

# --- Configuration ---
MATRIX_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+-=[]{};:'\"\\|,./<>?`~"
ANIMATION_DELAY = 0.05
MIN_STREAK_LENGTH = 10
MAX_STREAK_LENGTH = 30
MIN_STREAK_SPEED = 1
MAX_STREAK_SPEED = 3
STREAK_DENSITY = 0.5

TETRIS_BOARD_WIDTH = 10
TETRIS_BOARD_HEIGHT = 20
TETROMINOES = [
    # I shape
    [[1, 1, 1, 1]],
    # O shape
    [[1, 1], [1, 1]],
    # T shape
    [[0, 1, 0], [1, 1, 1]],
    # S shape
    [[0, 1, 1], [1, 1, 0]],
    # Z shape
    [[1, 1, 0], [0, 1, 1]],
    # J shape
    [[1, 0, 0], [1, 1, 1]],
    # L shape
    [[0, 0, 1], [1, 1, 1]],
]

# Adjust this value to change the game speed
FALL_SPEED = 0.8

# --- Global Variables ---
streaks = []
screen_height, screen_width = 0, 0
current_buffer = []

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

def draw_seamless_rain_background(stdscr, color_pair):
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    for streak in streaks:
        for i in range(streak['length']):
            y_pos = streak['y'] + i
            x_pos = streak['x']
            if 0 <= y_pos < height and 0 <= x_pos < width:
                char_to_draw = streak['char_set'][i]
                stdscr.addstr(y_pos, x_pos, char_to_draw, color_pair)

        streak['y'] += streak['speed']
        
        if streak['y'] > height:
            streak['y'] = random.randint(-height, 0)
            streak['length'] = random.randint(MIN_STREAK_LENGTH, MAX_STREAK_LENGTH)
            streak['speed'] = random.randint(MIN_STREAK_SPEED, MAX_STREAK_SPEED)
            streak['char_set'] = [random.choice(MATRIX_CHARS) for _ in range(streak['length'])]

def draw_game_board_and_pieces(stdscr, board, current_piece, score, color_pair):
    height, width = stdscr.getmaxyx()
    board_start_y = (height - TETRIS_BOARD_HEIGHT) // 2
    board_start_x = (width - TETRIS_BOARD_WIDTH * 2) // 2
    
    for y in range(TETRIS_BOARD_HEIGHT + 2):
        if 0 <= board_start_y + y - 1 < height:
            stdscr.addstr(board_start_y + y - 1, board_start_x - 1, "+" + "-" * (TETRIS_BOARD_WIDTH * 2) + "+", color_pair)
    for y in range(TETRIS_BOARD_HEIGHT):
        if 0 <= board_start_y + y < height:
            stdscr.addstr(board_start_y + y, board_start_x - 1, "|", color_pair)
            stdscr.addstr(board_start_y + y, board_start_x + TETRIS_BOARD_WIDTH * 2, "|", color_pair)
    if 0 <= board_start_y + TETRIS_BOARD_HEIGHT < height:
        stdscr.addstr(board_start_y + TETRIS_BOARD_HEIGHT, board_start_x - 1, "+" + "-" * (TETRIS_BOARD_WIDTH * 2) + "+", color_pair)

    for y in range(TETRIS_BOARD_HEIGHT):
        for x in range(TETRIS_BOARD_WIDTH):
            if board[y][x] == 1:
                stdscr.addstr(board_start_y + y, board_start_x + x * 2, "[]", color_pair)

    for y_piece, row in enumerate(current_piece['shape']):
        for x_piece, cell in enumerate(row):
            if cell == 1:
                if 0 <= board_start_y + current_piece['y'] + y_piece < height and 0 <= board_start_x + (current_piece['x'] + x_piece) * 2 < width:
                    char = random.choice(MATRIX_CHARS)
                    stdscr.addstr(board_start_y + current_piece['y'] + y_piece, board_start_x + (current_piece['x'] + x_piece) * 2, char + " ", color_pair)
    
    score_y = board_start_y + TETRIS_BOARD_HEIGHT + 2
    score_x = board_start_x
    if 0 <= score_y < height:
        stdscr.addstr(score_y, score_x, f"Score: {score}", color_pair)

def check_collision(board, piece, y, x):
    for row_idx, row in enumerate(piece):
        for col_idx, cell in enumerate(row):
            if cell == 1:
                if x + col_idx < 0 or x + col_idx >= TETRIS_BOARD_WIDTH or y + row_idx >= TETRIS_BOARD_HEIGHT:
                    return True
                if board[y + row_idx][x + col_idx] == 1:
                    return True
    return False

def rotate_piece(piece):
    return [list(row) for row in zip(*piece[::-1])]

def main(stdscr):
    global streaks, screen_height, screen_width
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
    
    board = [[0] * TETRIS_BOARD_WIDTH for _ in range(TETRIS_BOARD_HEIGHT)]
    score = 0
    game_over = False
    
    current_piece = {
        'shape': random.choice(TETROMINOES),
        'x': TETRIS_BOARD_WIDTH // 2,
        'y': 0
    }
    
    last_fall_time = time.time()
    
    while not game_over:
        draw_seamless_rain_background(stdscr, color_pair)
        draw_game_board_and_pieces(stdscr, board, current_piece, score, color_pair)
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key != -1:
            if key == ord('q'):
                break
            elif key == curses.KEY_LEFT:
                if not check_collision(board, current_piece['shape'], current_piece['y'], current_piece['x'] - 1):
                    current_piece['x'] -= 1
            elif key == curses.KEY_RIGHT:
                if not check_collision(board, current_piece['shape'], current_piece['y'], current_piece['x'] + 1):
                    current_piece['x'] += 1
            elif key == curses.KEY_UP:
                rotated_piece = rotate_piece(current_piece['shape'])
                if not check_collision(board, rotated_piece, current_piece['y'], current_piece['x']):
                    current_piece['shape'] = rotated_piece
            elif key == curses.KEY_DOWN:
                if not check_collision(board, current_piece['shape'], current_piece['y'] + 1, current_piece['x']):
                    current_piece['y'] += 1
            elif key == ord(' '):
                while not check_collision(board, current_piece['shape'], current_piece['y'] + 1, current_piece['x']):
                    current_piece['y'] += 1
        
        if time.time() - last_fall_time > FALL_SPEED:
            if check_collision(board, current_piece['shape'], current_piece['y'] + 1, current_piece['x']):
                for y_piece, row in enumerate(current_piece['shape']):
                    for x_piece, cell in enumerate(row):
                        if cell == 1:
                            if 0 <= current_piece['y'] + y_piece < TETRIS_BOARD_HEIGHT and 0 <= current_piece['x'] + x_piece < TETRIS_BOARD_WIDTH:
                                board[current_piece['y'] + y_piece][current_piece['x'] + x_piece] = 1
                
                lines_cleared = 0
                for y in range(TETRIS_BOARD_HEIGHT):
                    if all(board[y]):
                        board.pop(y)
                        board.insert(0, [0] * TETRIS_BOARD_WIDTH)
                        lines_cleared += 1
                score += lines_cleared * 100
                
                if any(board[0]):
                    game_over = True

                current_piece['shape'] = random.choice(TETROMINOES)
                current_piece['x'] = TETRIS_BOARD_WIDTH // 2 - len(current_piece['shape'][0]) // 2
                current_piece['y'] = 0
            else:
                current_piece['y'] += 1
            last_fall_time = time.time()
            
        time.sleep(0.01)

    stdscr.clear()
    stdscr.refresh()
    
    if game_over:
        sys.exit(f"Game Over! Score: {score}")
    else:
        sys.exit(f"Quitting. Final Score: {score}")

if __name__ == '__main__':
    curses.wrapper(main)
