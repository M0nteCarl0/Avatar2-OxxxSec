#!/usr/bin/env python3
"""
Verification and Health-Check Suite for the Avatar2 Framework and all 30 post examples.
Checks the core engines, the presence of every post's README.md/example.py and that each
example compiles, then prints a per-post table.
"""

import os
import subprocess
import sys

# A single Telegram text message is capped at 4096 UTF-16 code units
# (every emoji counts twice), and every chapter README doubles as one post.
TELEGRAM_MESSAGE_LIMIT = 4096


def telegram_units(text: str) -> int:
    """Telegram measures message length in UTF-16 code units (emoji count twice)."""
    return len(text.encode("utf-16-le")) // 2


def _unicode_ok() -> bool:
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in encoding


def render_table(headers, rows, aligns=None) -> str:
    """Render an ASCII/Unicode box table (falls back to ASCII on legacy consoles)."""
    aligns = aligns or ["<"] * len(headers)
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))

    if _unicode_ok():
        h, v = "\u2500", "\u2502"
        tl, tm, tr = "\u250c", "\u252c", "\u2510"
        ml, mm, mr = "\u251c", "\u253c", "\u2524"
        bl, bm, br = "\u2514", "\u2534", "\u2518"
    else:
        h, v = "-", "|"
        tl = tm = tr = ml = mm = mr = bl = bm = br = "+"

    def border(left, middle, right):
        return left + middle.join(h * (width + 2) for width in widths) + right

    def row_line(cells):
        rendered = []
        for cell, width, align in zip(cells, widths, aligns):
            text = str(cell)
            rendered.append(" " + (text.ljust(width) if align == "<" else text.rjust(width)) + " ")
        return v + v.join(rendered) + v

    lines = [border(tl, tm, tr), row_line(headers), border(ml, mm, mr)]
    lines.extend(row_line(row) for row in rows)
    lines.append(border(bl, bm, br))
    return "\n".join(lines)


def check_avatar2_installation() -> bool:
    print("[*] Checking Avatar2 Framework core modules...")
    try:
        import avatar2
        from avatar2 import Avatar, TargetStates, ARM_CORTEX_M3  # noqa: F401
        from avatar2.targets import DummyTarget, UnicornTarget  # noqa: F401
        from avatar2.peripherals import AvatarPeripheral  # noqa: F401
        import unicorn
        import capstone
        import keystone

        print(render_table(
            ["Component", "Version / Location"],
            [
                ["avatar2", avatar2.__file__],
                ["unicorn", unicorn.__version__],
                ["capstone", capstone.__version__],
                ["keystone", keystone.__version__],
            ],
        ))
        print("  [+] Core emulation & orchestration engines: OK")
        return True
    except ImportError as error:
        print(f"  [-] Import error: {error}")
        return False


def verify_all_30_posts() -> bool:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    total_posts = 30
    rows = []
    passed_count = 0
    readme_units = {}
    longest_units = (0, "-")

    for number in range(1, total_posts + 1):
        prefix = f"{number:02d}_"
        matching = [
            d for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d)) and d.startswith(prefix)
        ]
        if not matching:
            rows.append((number, "-", "missing", "missing", "-", "FAIL"))
            continue

        folder = matching[0]
        script_path = os.path.join(base_dir, folder, "example.py")
        readme_path = os.path.join(base_dir, folder, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, encoding="utf-8") as handle:
                readme_units[number] = telegram_units(handle.read())
            readme_state = f"{readme_units[number]}"
        else:
            readme_state = "MISSING"

        if not os.path.exists(script_path):
            rows.append((number, folder, readme_state, "MISSING", "-", "FAIL"))
            continue

        result = subprocess.run(
            [sys.executable, "-m", "py_compile", script_path],
            capture_output=True, text=True,
        )
        compile_state = "OK" if result.returncode == 0 else "SYNTAX ERROR"
        readme_fits = readme_state != "MISSING" and readme_units[number] <= TELEGRAM_MESSAGE_LIMIT
        status = "PASS" if (result.returncode == 0 and readme_fits) else "FAIL"
        if status == "PASS":
            passed_count += 1
            if readme_units[number] > longest_units[0]:
                longest_units = (readme_units[number], folder)
        rows.append((number, folder, readme_state, "yes", compile_state, status))

    print()
    print(f"[*] Verifying {total_posts} post scripts in: {base_dir}")
    print(render_table(
        ["#", "Post directory", "README, uc", "example.py", "py_compile", "Status"],
        rows,
        aligns=[">", "<", ">", "<", "<", "<"],
    ))
    print(f"[*] README budget: {TELEGRAM_MESSAGE_LIMIT} UTF-16 units per post "
          f"(one Telegram message); longest: {longest_units[0]} ({longest_units[1]})")
    print(f"[*] Summary: {passed_count}/{total_posts} posts verified successfully.")
    return passed_count == total_posts


if __name__ == "__main__":
    if not check_avatar2_installation():
        print("[-] Avatar2 core components missing or broken. Please run the setup_env script.")
        sys.exit(1)

    if verify_all_30_posts():
        print("[+] All 30 post examples passed verification!")
        sys.exit(0)

    print("[-] Some examples failed verification.")
    sys.exit(1)
