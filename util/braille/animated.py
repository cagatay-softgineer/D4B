import sys
import time
import re



def animated_braille_slide_seamless(
    braille_text, width=80, delay=0.04, clear_screen=True
):
    """
    Continuously slides the given Braille art horizontally across the CLI, seamlessly.
    Args:
        braille_text: The multiline colored Braille string to slide.
        width: The width of the display area.
        delay: Delay between frames (seconds).
        clear_screen: Whether to clear the screen each frame.
    """
    lines = braille_text.splitlines()
    visible_lengths = [_len_visible(line) for line in lines]
    max_len = max(visible_lengths)
    double_lines = [line + line for line in lines]  # Seamless loop
    WHILE = True
    try:
        while WHILE:
            for offset in range(max_len):
                if clear_screen:
                    sys.stdout.write("\033[H\033[J")
                for i, dline in enumerate(double_lines):
                    visible = _ansi_slice(dline, offset, width)
                    print(visible, flush=True)
                sys.stdout.flush()
                time.sleep(delay)
                WHILE = False
    except KeyboardInterrupt:
        print("\nAnimation stopped.")

def _strip_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)

def _len_visible(s):
    return len(_strip_ansi(s))

def _ansi_slice(s, start, length):
    """ANSI-safe slice by visible chars, preserving color codes."""
    result = ""
    visible_count = 0
    i = 0
    # Skip to start
    while visible_count < start and i < len(s):
        if s[i] == "\033":
            m = re.match(r'\x1b\[[0-9;]*m', s[i:])
            if m:
                i += len(m.group())
                continue
        else:
            visible_count += 1
        i += 1
    # Now collect
    visible_count = 0
    start_i = i  # noqa: F841
    while visible_count < length and i < len(s):
        if s[i] == "\033":
            m = re.match(r'\x1b\[[0-9;]*m', s[i:])
            if m:
                result += m.group()
                i += len(m.group())
                continue
        else:
            visible_count += 1
        if visible_count <= length:
            result += s[i]
        i += 1
    result += "\033[0m"
    return result

# Example Usage:
if __name__ == "__main__":
    from util.braille.text_braille import text_to_centered_inverted_braille_colored
    braille_text = text_to_centered_inverted_braille_colored(
        "D4B Starship", font_size=28, padding=10
    )
    animated_braille_slide_seamless(braille_text, width=80, delay=0.05)
