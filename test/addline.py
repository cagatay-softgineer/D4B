import os
import random
import sys
import time
from colorama import init

init()

COLORS = [
    "\033[91m",  # Red
    "\033[92m",  # Green
    "\033[93m",  # Yellow
    "\033[94m",  # Blue
    "\033[95m",  # Magenta
    "\033[96m",  # Cyan
    "\033[97m",  # White
    "\033[90m",  # Bright Black (Gray)
]
RESET = "\033[0m"
COLS = 80
LINE_COUNT = 5

# Define various pattern sets
PATTERN_SETS = [
    ['\\', '/'],
    ['-', '|', '+'],
    ['*', '.', 'o', '+'],
    ['█', '▓', '▒', '░'],
    ['→', '←', '↑', '↓'],
    ['~', '-', '_', '^'],
    ['x', 'o', 'O'],
    ['─', '│', '┌', '┐', '└', '┘', '┼', '├', '┤', '┬', '┴'],
    [chr(i) for i in range(0x2800, 0x28FF)],  # Braille
]

def clear_output():
    os.system("cls" if os.name == "nt" else "clear")

def print_pattern(lines=LINE_COUNT, cols=COLS):
    for _ in range(lines):
        # Randomly choose a pattern for this line
        pattern_chars = random.choice(PATTERN_SETS)
        for _ in range(cols):
            char = random.choice(pattern_chars)
            color = random.choice(COLORS)
            sys.stdout.write(f"{color}{char}{RESET}")
        sys.stdout.write('\n')
    sys.stdout.flush()

def print_welcome():
    sys.stdout.write("\n")
    sys.stdout.write("\t" * random.randint(0, 6) + "D4B System Is Loading...\n")
    sys.stdout.write("\n")
    sys.stdout.flush()

if __name__ == "__main__":
    while True:
        clear_output()
        print_pattern()
        print_welcome()
        print_pattern()
        time.sleep(0.5)
