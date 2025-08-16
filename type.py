import curses
import time
import sys

# --- Configuration ---
TYPING_QUOTE = "The Matrix is a system, Neo. That system is our enemy."
ANIMATION_DELAY = 0.05

def main(stdscr):
    # Set up curses environment
    curses.curs_set(1)  # Show the cursor
    stdscr.nodelay(True) # Non-blocking input
    stdscr.timeout(0)    # No wait for input
    
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        color_pair = curses.color_pair(1)
    else:
        color_pair = 0

    stdscr.clear()
    
    typed_text = ""
    start_time = None
    
    while True:
        stdscr.erase()
        height, width = stdscr.getmaxyx()
        
        # Center the quote on the screen
        quote_y = height // 2 - 2
        input_y = height // 2
        quote_x = (width - len(TYPING_QUOTE)) // 2
        
        stdscr.addstr(quote_y, quote_x, TYPING_QUOTE, color_pair)
        stdscr.addstr(input_y, quote_x, typed_text, color_pair)
        stdscr.refresh()
        
        key = stdscr.getch()
        
        if key != -1:
            if not start_time:
                start_time = time.time()
                
            if key == curses.KEY_ENTER or key == ord('\n'):
                # Calculate WPM and accuracy
                time_taken = time.time() - start_time if start_time else 0
                word_count = len(typed_text.split())
                words_per_minute = (word_count / time_taken) * 60 if time_taken > 0 else 0
                
                correct_chars = sum(1 for i, char in enumerate(typed_text) if i < len(TYPING_QUOTE) and char == TYPING_QUOTE[i])
                accuracy = (correct_chars / len(TYPING_QUOTE)) * 100 if len(TYPING_QUOTE) > 0 else 0
                
                # Print the final results to stdout before exiting
                sys.stdout.write(f"WPM: {words_per_minute:.2f}\nAccuracy: {accuracy:.2f}%")
                sys.exit()

            elif key == curses.KEY_BACKSPACE or key == ord('\b'):
                typed_text = typed_text[:-1]
            elif 32 <= key < 127:
                if len(typed_text) < len(TYPING_QUOTE):
                    typed_text += chr(key)
        
        time.sleep(ANIMATION_DELAY)

if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except SystemExit as e:
        # Catch the exit code from inside the curses app
        sys.exit(e.code)
    except Exception:
        # Fallback for other errors
        sys.exit("An error occurred during the typing test.")
