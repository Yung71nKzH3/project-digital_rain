import curses
import random
import time
import sys
import os

# --- Configuration ---
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

FALL_SPEED = 0.8
RAIN_UPDATE_SPEED = 0.1
MATRIX_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+-=[]{};:'\"\\|,./<>?`~"

streaks = []
screen_height, screen_width = 0, 0

def create_streaks(width, height):
    streaks = []
    num_streaks = int(width * 0.5)
    for _ in range(num_streaks):
        x = random.randint(0, width - 1)
        y = random.randint(-height, 0)
        length = random.randint(10, 30)
        speed = 1
        char_set = [random.choice(MATRIX_CHARS) for _ in range(length)]
        streaks.append({'x': x, 'y': y, 'length': length, 'speed': speed, 'char_set': char_set})
    return streaks

def draw_seamless_rain_background(stdscr, color_pair, update_rain=False):
    """Draws the falling rain to fill the background."""
    height, width = stdscr.getmaxyx()
    stdscr.erase()
    
    for streak in streaks:
        for i in range(streak['length']):
            y_pos = streak['y'] + i
            x_pos = streak['x']
            
            if 0 <= y_pos < height and 0 <= x_pos < width:
                char_to_draw = streak['char_set'][i]
                try:
                    stdscr.addstr(y_pos, x_pos, char_to_draw, color_pair)
                except curses.error:
                    pass
    
        if update_rain:
            streak['y'] += streak['speed']
            
        if streak['y'] > height:
            streak['y'] = random.randint(-height, 0)
            streak['length'] = random.randint(10, 30)
            streak['speed'] = random.randint(1, 3)
            streak['char_set'] = [random.choice(MATRIX_CHARS) for _ in range(streak['length'])]

def draw_game_board_and_pieces(stdscr, board, current_piece, score, color_pair):
    height, width = stdscr.getmaxyx()
    board_start_y = (height - TETRIS_BOARD_HEIGHT) // 2
    board_start_x = (width - TETRIS_BOARD_WIDTH * 2) // 2
    
    # Draw background box
    for y in range(TETRIS_BOARD_HEIGHT + 2):
        for x in range(TETRIS_BOARD_WIDTH * 2 + 2):
            if 0 <= board_start_y + y - 1 < height and 0 <= board_start_x + x - 1 < width:
                try:
                    stdscr.addstr(board_start_y + y - 1, board_start_x + x - 1, " ", curses.color_pair(2))
                except curses.error: pass

    # Draw existing board pieces
    for y in range(TETRIS_BOARD_HEIGHT):
        for x in range(TETRIS_BOARD_WIDTH):
            if board[y][x] == 1:
                try:
                    stdscr.addstr(board_start_y + y, board_start_x + x * 2, "[]", color_pair)
                except curses.error: pass

    # Draw current piece
    for y_piece, row in enumerate(current_piece['shape']):
        for x_piece, cell in enumerate(row):
            if cell == 1:
                if 0 <= board_start_y + current_piece['y'] + y_piece < height:
                    char = random.choice(MATRIX_CHARS)
                    try:
                        stdscr.addstr(board_start_y + current_piece['y'] + y_piece, board_start_x + (current_piece['x'] + x_piece) * 2, char + " ", color_pair)
                    except curses.error: pass
    
    score_y = board_start_y + TETRIS_BOARD_HEIGHT + 2
    score_x = board_start_x
    if 0 <= score_y < height:
        try:
            stdscr.addstr(score_y, score_x, f"Score: {score}", color_pair)
        except curses.error: pass

def check_collision(board, piece, y, x):
    for row_idx, row in enumerate(piece):
        for col_idx, cell in enumerate(row):
            if cell == 1:
                if x + col_idx < 0 or x + col_idx >= TETRIS_BOARD_WIDTH or y + row_idx >= TETRIS_BOARD_HEIGHT:
                    return True
                if y + row_idx >= 0 and board[y + row_idx][x + col_idx] == 1:
                    return True
    return False

def rotate_piece(piece):
    return [list(row) for row in zip(*piece[::-1])]

def main(stdscr):
    global streaks, screen_height, screen_width
    
    # --- SETUP ---
    curses.curs_set(0) # Hide cursor for game
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
    
    board = [[0] * TETRIS_BOARD_WIDTH for _ in range(TETRIS_BOARD_HEIGHT)]
    score = 0
    game_over = False
    
    # Spawn first piece correctly centered
    shape = random.choice(TETROMINOES)
    current_piece = {
        'shape': shape,
        'x': TETRIS_BOARD_WIDTH // 2 - len(shape[0]) // 2,
        'y': 0
    }
    
    last_fall_time = time.time()
    last_rain_time = time.time()
    
    # --- GAME LOOP ---
    while not game_over:
        new_height, new_width = stdscr.getmaxyx()
        if (new_height, new_width) != (screen_height, new_width):
            screen_height, screen_width = new_height, new_width
            stdscr.clear()
            streaks = create_streaks(screen_width, screen_height)
        
        update_rain = False
        if time.time() - last_rain_time > RAIN_UPDATE_SPEED:
            update_rain = True
            last_rain_time = time.time()
            
        draw_seamless_rain_background(stdscr, color_pair, update_rain)
        draw_game_board_and_pieces(stdscr, board, current_piece, score, color_pair)
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key != -1:
            if key == ord('q'):
                return # Exit back to Matrix, don't kill process
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

                shape = random.choice(TETROMINOES)
                current_piece = {
                    'shape': shape,
                    'x': TETRIS_BOARD_WIDTH // 2 - len(shape[0]) // 2,
                    'y': 0
                }
            else:
                current_piece['y'] += 1
            last_fall_time = time.time()
            
        time.sleep(0.01)

    # Game Over Screen
    stdscr.nodelay(False) # Wait for input
    stdscr.clear()
    msg = f"GAME OVER - Score: {score}"
    h, w = stdscr.getmaxyx()
    stdscr.addstr(h//2, (w-len(msg))//2, msg, color_pair | curses.A_BOLD)
    stdscr.addstr(h//2 + 1, (w-20)//2, "Press any key to exit", color_pair)
    stdscr.refresh()
    stdscr.getch()

if __name__ == '__main__':
    curses.wrapper(main)