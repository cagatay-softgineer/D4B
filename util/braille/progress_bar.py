import random
import sys
import time


def braille_progress_bar_with_percent(
    progress, length=18, color="\033[96m", reset="\033[0m", show_percent=True
):
    fill_order = [0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80]
    total_dots = length * 8
    filled = int(round(progress * total_dots))
    chars = []
    for i in range(length):
        dots_in_cell = min(8, max(0, filled - i * 8))
        cell = 0
        for j in range(dots_in_cell):
            cell |= fill_order[j]
        chars.append(chr(0x2800 + cell))
    bar = color + "".join(chars) + reset
    if show_percent:
        percent = f" {int(progress * 100):3d}%"
        bar += percent
    return bar


def animate_braille_bar_line(
    name,
    result,
    progress,
    RESET,  # noqa: F811
    bar_length=18,
    stat_color="\033[92m",
    mark="[✓]",
    sleep=0.01,
):
    """
    Animates a single line with a Braille progress bar filling from left to right,
    then prints the full result line with check status.
    """
    total_steps = bar_length * 8  # Each dot is a step
    for i in range(1, total_steps + 1):
        current_prog = (i / total_steps) * progress
        bar = braille_progress_bar_with_percent(
            current_prog, bar_length, color="\033[96m"
        )
        # \r to overwrite, but pad with spaces in case of shorter line
        sys.stdout.write(f"\r{mark} {name:<22}      {bar}   ")
        sys.stdout.flush()
        time.sleep(sleep)
    # After full bar, show result and status
    sys.stdout.write("\r")  # Start of line again

    sys.stdout.flush()
    bar_str = braille_progress_bar_with_percent(progress, bar_length, color="\033[96m")
    sys.stdout.write(f"{mark} {name:<22} {bar_str} {stat_color}{result:<5}{RESET}\n")
    sys.stdout.flush()

def ease_out_cubic(x: float) -> float:
    """Cubic ease‑out: fast start, slow finish (x in [0,1])."""
    return 1 - (1 - x) ** 3

def animate_multiple_braille_bars(
    services,
    bar_length=18,
    min_frames=40,
    max_frames=80,
    delay=0.04,
    fail_freeze_range=(0.2, 0.7),
    finish_effect_frames=10,
    flash_period=10,
):
    """
    Animate multiple Braille bars with ease‑out, fail‑freeze, per‑status flourish,
    and then a final uniform finish color by status.

    services: list of dicts:
      - name            (str)
      - status          ("OK","WARN","FAIL")
      - target_progress (float, usually 1.0)
    """
    # Map status → finish background
    finish_bg_map = {
        "OK":   "\033[42m",  # Green background
        "WARN": "\033[43m",  # Yellow background
        "FAIL": "\033[41m",  # Red background
    }

    # Prepare animation parameters for each service
    styled = []
    for s in services:
        st    = s["status"]
        mark  = {"OK":"[✓]","WARN":"[!]","FAIL":"[X]"}[st]
        col   = {"OK":"\033[92m","WARN":"\033[93m","FAIL":"\033[91m"}[st]
        frames = random.randint(min_frames, max_frames)
        freeze_pt = None
        if st == "FAIL":
            freeze_pt = random.uniform(*fail_freeze_range) * s["target_progress"]
        styled.append({
            "name":       s["name"],
            "mark":       mark,
            "color":      col,
            "status":     st,
            "frames":     frames,
            "target":     s["target_progress"],
            "freeze_at":  freeze_pt,
            "finish_bg":  finish_bg_map[st],
        })

    total = len(styled)
    # Reserve lines
    for _ in styled:
        print()

    max_frames = max(s["frames"] for s in styled)
    end_frame  = max_frames + finish_effect_frames

    for frame in range(1, end_frame + 1):
        sys.stdout.write(f"\033[{total}A")  # move cursor up

        for svc in styled:
            name, mark, color, status = svc["name"], svc["mark"], svc["color"], svc["status"]
            t, tgt, freeze_at, finish_bg = svc["frames"], svc["target"], svc["freeze_at"], svc["finish_bg"]

            if frame <= t:
                # in‑flight animation
                raw = frame / t
                if status in ("OK","WARN"):
                    prog = ease_out_cubic(raw) * tgt
                else:
                    prog = raw * tgt
                    if freeze_at and prog >= freeze_at:
                        prog = freeze_at
                bar = braille_progress_bar_with_percent(prog, bar_length, color=color)
                label = ""
            else:
                eff = frame - t
                full = braille_progress_bar_with_percent(tgt, bar_length, color=color)

                if eff < finish_effect_frames:
                    # per‑status flourish
                    if status == "OK":
                        # pulse white
                        if (eff // 2) % 2 == 0:
                            bar = "\033[107m" + " " * bar_length + "\033[0m"
                        else:
                            bar = full
                        label = ""
                    elif status == "WARN":
                        # flash yellow bg
                        if eff % flash_period < (flash_period // 2):
                            bar = "\033[43m" + " " * bar_length + "\033[0m"
                        else:
                            bar = full
                        label = ""
                    else:  # FAIL
                        # flash red bg
                        if eff % flash_period < (flash_period // 2):
                            bar = "\033[41m" + " " * bar_length + "\033[0m"
                        else:
                            bar = full
                        label = ""
                else:
                    # final uniform finish background + percent + status
                    bar = finish_bg + " " * bar_length + "\033[0m"
                    label = f" {int(tgt * 100):3d}% {status}"

            sys.stdout.write(f"{mark} {name:<22} {bar}{label}\n")

        sys.stdout.flush()
        time.sleep(delay)

def advanced_animate_braille_bar_line(name, result, progress, RESET, bar_length=18, stat_color="\033[92m", mark="[✓]", sleep=0.01):  # noqa: F811
    """
    Animates a single line with a Braille progress bar filling from left to right.
    On FAIL, fills only to 50%, flashes red, then fills to 100% with a FAIL color.
    """
    # Set color according to status
    if result == "OK":
        bar_color = "\033[92m"   # Green
        full_prog = progress
        fill_to = bar_length * 8
        emoji = ""
    elif result == "WARN":
        bar_color = "\033[93m"   # Yellow
        full_prog = progress
        fill_to = bar_length * 8  # noqa: F841
        emoji = " ⚠️"
    else:  # FAIL
        bar_color = "\033[91m"   # Red
        # Animate to 50% then fill rest, for effect
        half_steps = (bar_length * 8) // 2
        # Animate bar to half (with red color)
        for i in range(1, half_steps + 1):
            current_prog = (i / (bar_length * 8)) * 0.5  # Up to 50%
            bar = braille_progress_bar_with_percent(current_prog, bar_length, color=bar_color)
            sys.stdout.write(f"\r{mark} {name:<22}      {bar}   ")
            sys.stdout.flush()
            time.sleep(sleep * 2)  # Slightly slower for drama
        # Flash or fill the rest with cross pattern or block (simulate "fail")
        for j in range(3):
            # Flash blank, then fail pattern
            if j % 2 == 0:
                fail_bar = "\033[41m" + " " * bar_length + "\033[0m"
            else:
                fail_bar = braille_progress_bar_with_percent(1.0, bar_length, color=bar_color)
            sys.stdout.write(f"\r{mark} {name:<22}      {fail_bar}   ")
            sys.stdout.flush()
            time.sleep(0.18)
        emoji = " ✗"
        sys.stdout.write("\r")
        final_bar = braille_progress_bar_with_percent(1.0, bar_length, color=bar_color)
        sys.stdout.write(f"{mark} {name:<22} {stat_color}{result:<5}{RESET}  {final_bar}{emoji}\n")
        sys.stdout.flush()
        return  # Early return so OK/WARN doesn't also run below

    # For OK and WARN (and for FAIL after fail effect)
    total_steps = bar_length * 8  # Each dot is a step
    for i in range(1, total_steps + 1):
        current_prog = (i / total_steps) * full_prog
        bar = braille_progress_bar_with_percent(current_prog, bar_length, color=bar_color)
        sys.stdout.write(f"\r{mark} {name:<22}      {bar}   ")
        sys.stdout.flush()
        time.sleep(sleep)
    sys.stdout.write("\r")
    final_bar = braille_progress_bar_with_percent(full_prog, bar_length, color=bar_color)
    sys.stdout.write(f"{mark} {name:<22} {stat_color}{result:<5}{RESET}  {final_bar}{emoji}\n")
    sys.stdout.flush()

# Example usage:
if __name__ == "__main__":
    import time
    import sys

    for i in range(0, 101):
        p = i / 100
        sys.stdout.write(f"\r{braille_progress_bar_with_percent(p, 32)}")
        sys.stdout.flush()
        time.sleep(0.03)
    print()
