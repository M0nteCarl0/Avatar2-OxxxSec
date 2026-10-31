#!/usr/bin/env python3
"""
Master runner script:
Executes example.py across all 30 posts (01 to 30) and writes three artifacts into every post
folder: run.log (raw stdout/stderr), run_report.md (status table + output) and
run_screenshot.svg (a terminal-style screenshot of the real execution).  A summary table for the
whole suite is printed at the end.  Only example-relative names are used - no absolute paths.
"""

import os
import subprocess
import sys
import time

TIMEOUT_SECONDS = 45
MAX_COLS = 108
CHAR_WIDTH = 7.8
LINE_HEIGHT = 19
PADDING = 18
TITLE_HEIGHT = 34
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"


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


def resolve_interpreter(repo_root: str) -> tuple:
    """Prefer the project virtualenv when it exists (Windows and POSIX layouts)."""
    candidates = [
        os.path.join(repo_root, ".venv", "Scripts", "python.exe"),
        os.path.join(repo_root, ".venv", "bin", "python"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate, True
    return sys.executable, False


def interpreter_label(in_venv: bool) -> str:
    """Human readable interpreter without leaking an absolute path into the artifacts."""
    version = sys.version.split()[0]
    return "python %s (.venv)" % version if in_venv else "python %s" % version


def build_log(stdout: str, stderr: str, returncode: int) -> str:
    """The log holds the real program output; stderr is appended in its own section."""
    content = stdout or ""
    if stderr:
        if content and not content.endswith("\n"):
            content += "\n"
        content += "\n--- STDERR ---\n" + stderr
    if not content.strip():
        content = "(no output captured)\n"
    if returncode != 0:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n--- EXIT CODE: %d ---\n" % returncode
    return content


def _fence_for(text: str) -> str:
    """Pick a code fence that cannot be closed by the captured output itself."""
    longest = current = 0
    for char in text:
        current = current + 1 if char == "`" else 0
        longest = max(longest, current)
    return "`" * max(3, longest + 1)


def _xml_escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace('"', "&quot;"))


def _line_color(line: str) -> str:
    if line.startswith("[SUCCESS]"):
        return "#3fb950"
    if line.startswith("[i]"):
        return "#d29922"
    if line.startswith(("[!]", "[-]")):
        return "#f85149"
    if line.startswith("[+]"):
        return "#79c0ff"
    return "#c9d1d9"


def build_screenshot_svg(folder: str, output: str) -> str:
    """Terminal-style SVG screenshot of the captured output (text, no external assets)."""
    body = []
    for raw in output.rstrip("\n").split("\n"):
        if not raw:
            body.append("")
            continue
        while len(raw) > MAX_COLS:
            body.append(raw[:MAX_COLS])
            raw = raw[MAX_COLS:]
        body.append(raw)

    rows = [("$ python example.py", "#7ee787")] + [(line, _line_color(line)) for line in body] + [("$", "#7ee787")]
    columns = max([len(text) for text, _color in rows] + [len(folder), 20])
    columns = min(columns, MAX_COLS + 2)

    width = int(PADDING * 2 + columns * CHAR_WIDTH)
    height = int(TITLE_HEIGHT + PADDING * 2 + len(rows) * LINE_HEIGHT)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="Terminal output of %s">' % (width, height, width, height, _xml_escape(folder)),
        '  <rect width="%d" height="%d" rx="10" fill="#0d1117"/>' % (width, height),
        '  <rect width="%d" height="%d" rx="10" fill="#161b22"/>' % (width, TITLE_HEIGHT),
        '  <circle cx="18" cy="%d" r="6" fill="#ff5f56"/>' % (TITLE_HEIGHT // 2),
        '  <circle cx="38" cy="%d" r="6" fill="#ffbd2e"/>' % (TITLE_HEIGHT // 2),
        '  <circle cx="58" cy="%d" r="6" fill="#27c93f"/>' % (TITLE_HEIGHT // 2),
        '  <text x="80" y="%d" fill="#8b949e" font-family="%s" font-size="12">%s</text>'
        % (TITLE_HEIGHT // 2 + 4, FONT, _xml_escape(folder)),
        '  <g font-family="%s" font-size="13" xml:space="preserve">' % FONT,
    ]

    y = TITLE_HEIGHT + PADDING + 12
    for text, color in rows:
        parts.append('    <text x="%d" y="%d" fill="%s">%s</text>'
                     % (PADDING, y, color, _xml_escape(text)))
        y += LINE_HEIGHT
    parts.append("  </g>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def build_report(folder: str, status: str, returncode, duration: float,
                 output: str, interpreter: str, png_ready: bool) -> str:
    """Markdown report: machine-readable status table + screenshot + captured output."""
    fence = _fence_for(output)
    artifacts = "[run.log](run.log) - [run_screenshot.svg](run_screenshot.svg)"
    if png_ready:
        artifacts += " - [Telegram PNG](../telegram_assets/%s.png)" % folder
    rows = [
        ("Example", "`%s`" % folder),
        ("Status", "**%s**" % status),
        ("Exit code", "`%s`" % ("-" if returncode is None else returncode)),
        ("Duration", "%.2f s" % duration),
        ("Output lines", str(output.count("\n"))),
        ("Output size", "%d B" % len(output.encode("utf-8"))),
        ("Command", "`python example.py`, `./run.sh` or `.\\run.ps1` (inside the example folder)"),
        ("Interpreter", "`%s`" % interpreter),
        ("Artifacts", artifacts),
    ]
    table = ["| Field | Value |", "|:--|:--|"]
    table.extend("| %s | %s |" % (name, value) for name, value in rows)
    screenshot_lines = ["## Screenshot", "", "![Terminal screenshot of %s](run_screenshot.svg)" % folder]
    if png_ready:
        screenshot_lines += ["", "Telegram-ready raster copy: "
                                 "[`../telegram_assets/%s.png`](../telegram_assets/%s.png)" % (folder, folder)]
    return "\n".join([
        "# Run report: %s" % folder,
        "",
        "Generated by `run_all_and_log.py`; everything below comes from a real local run of "
        "`example.py`.",
        "",
        "## Status",
        "",
        *table,
        "",
        *screenshot_lines,
        "",
        "## Output",
        "",
        fence + "text",
        output.rstrip("\n"),
        fence,
        "",
    ])


def _load_mono_font(size: int):
    """Best-effort monospace TrueType font for the PNG export."""
    from PIL import ImageFont

    candidates = [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def export_telegram_png(folder: str, output: str, path: str) -> bool:
    """Rasterise the captured run into a Telegram-friendly PNG (returns False if Pillow is absent)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    scale = 2  # render at 2x so the picture stays sharp in Telegram
    font_size = 13 * scale
    line_height = LINE_HEIGHT * scale
    padding = PADDING * scale
    title_height = TITLE_HEIGHT * scale

    font = _load_mono_font(font_size)
    title_font = _load_mono_font(11 * scale)
    char_width = max(font.getlength("M"), 1.0)

    lines = []
    for raw in output.rstrip("\n").split("\n"):
        if not raw:
            lines.append("")
            continue
        while len(raw) > MAX_COLS:
            lines.append(raw[:MAX_COLS])
            raw = raw[MAX_COLS:]
        lines.append(raw)

    rows = [("$ python example.py", "#7ee787")] + [(line, _line_color(line)) for line in lines]
    rows.append(("$", "#7ee787"))

    columns = max([len(text) for text, _color in rows] + [len(folder), 20])
    columns = min(columns, MAX_COLS + 2)
    width = int(padding * 2 + columns * char_width)
    height = int(title_height + padding * 2 + len(rows) * line_height)

    image = Image.new("RGB", (width, height), "#0d1117")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, title_height], fill="#161b22")
    for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        cx = padding + index * 20 * scale // 2
        cy = title_height // 2
        radius = 6 * scale // 2
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)
    draw.text((80 * scale // 2 + padding // 2, title_height // 2 - 6 * scale),
              folder, font=title_font, fill="#8b949e")

    y = title_height + padding
    for text, color in rows:
        draw.text((padding, y), text, font=font, fill=color)
        y += line_height

    # Palette quantisation keeps the file small: text-only screenshots need very few colours
    palette_image = image.convert("P", palette=Image.ADAPTIVE, colors=32)
    palette_image.save(path, "PNG", optimize=True)
    return True


def write_artifacts(folder_path: str, folder: str, status: str, returncode,
                    duration: float, output: str, interpreter: str,
                    telegram_dir) -> tuple:
    log_path = os.path.join(folder_path, "run.log")
    report_path = os.path.join(folder_path, "run_report.md")
    shot_path = os.path.join(folder_path, "run_screenshot.svg")

    png_path = None
    png_ready = False
    if telegram_dir is not None:
        png_path = os.path.join(telegram_dir, "%s.png" % folder)
        png_ready = export_telegram_png(folder, output, png_path)

    with open(log_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(output)
    with open(report_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_report(folder, status, returncode, duration, output, interpreter, png_ready))
    with open(shot_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_screenshot_svg(folder, output))

    png_size = os.path.getsize(png_path) if png_ready and os.path.exists(png_path) else 0
    return os.path.getsize(log_path), os.path.getsize(shot_path), png_size


def main() -> int:
    repo_root = os.path.dirname(os.path.abspath(__file__))
    python_exe, in_venv = resolve_interpreter(repo_root)
    interpreter = interpreter_label(in_venv)

    dirs = [
        d for d in os.listdir(repo_root)
        if os.path.isdir(os.path.join(repo_root, d))
        and len(d) > 3 and d[:2].isdigit() and d[2] == "_"
    ]
    dirs.sort(key=lambda name: int(name[:2]))

    telegram_dir = os.path.join(repo_root, "telegram_assets")
    os.makedirs(telegram_dir, exist_ok=True)

    print(f"[*] Interpreter  : {interpreter}")
    print("[*] Artifacts    : run.log + run_report.md + run_screenshot.svg per example")
    print("[*] Telegram     : telegram_assets/<example>.png (one PNG per post)")
    print(f"[*] Examples     : {len(dirs)}")
    print()

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    rows = []
    failures = []
    bytes_total = 0
    started = time.time()

    for folder in dirs:
        folder_path = os.path.join(repo_root, folder)
        script_path = os.path.join(folder_path, "example.py")

        if not os.path.exists(script_path):
            output = "(no example.py in this folder)\n"
            write_artifacts(folder_path, folder, "MISSING", None, 0.0, output, interpreter,
                            telegram_dir)
            rows.append((folder[:2], folder, "MISSING", "-", "-", "-", "-", "-", "-"))
            failures.append((folder, "example.py not found", ""))
            continue

        started_at = time.time()
        status, returncode, output = "PASS", 0, ""
        try:
            proc = subprocess.run(
                [python_exe, script_path],
                cwd=repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=TIMEOUT_SECONDS,
            )
            duration = round(time.time() - started_at, 2)
            returncode = proc.returncode
            output = build_log(proc.stdout, proc.stderr, proc.returncode)
            status = "PASS" if proc.returncode == 0 else "FAIL"
            if proc.returncode != 0:
                failures.append((folder, "exit code %d" % proc.returncode,
                                 (proc.stderr or proc.stdout or "")[:800]))
        except subprocess.TimeoutExpired as expired:
            duration = round(time.time() - started_at, 2)
            partial = expired.stdout if isinstance(expired.stdout, str) else ""
            output = (partial + ("\n" if partial else "")
                      + "--- TIMEOUT after %.2f s (limit %d s) ---\n" % (duration, TIMEOUT_SECONDS))
            status, returncode = "TIMEOUT", None
            failures.append((folder, "timeout after %.2f s" % duration, ""))
        except Exception as error:  # noqa: BLE001 - the runner must never crash mid-suite
            duration = round(time.time() - started_at, 2)
            output = "--- RUNNER ERROR after %.2f s: %s ---\n" % (duration, error)
            status, returncode = "RUNNER ERROR", None
            failures.append((folder, "runner error: %s" % error, ""))

        log_bytes, shot_bytes, png_bytes = write_artifacts(folder_path, folder, status, returncode,
                                                           duration, output, interpreter,
                                                           telegram_dir)
        bytes_total += log_bytes + shot_bytes + png_bytes
        rows.append((folder[:2], folder, status,
                     "-" if returncode is None else returncode,
                     "%.2f" % duration, output.count("\n"),
                     "%d B" % log_bytes, "%d B" % shot_bytes,
                     "%d B" % png_bytes if png_bytes else "-"))

    total = round(time.time() - started, 2)
    passed = sum(1 for row in rows if row[2] == "PASS")

    print(render_table(
        ["#", "Example", "Status", "Exit", "Time, s", "Lines", "Log", "SVG", "Telegram PNG"],
        rows,
        aligns=[">", "<", "<", ">", ">", ">", ">", ">", ">"],
    ))
    print()
    print(f"[*] Result: {passed}/{len(dirs)} PASS | total {total:.2f} s | "
          f"{bytes_total} B written to run.log + run_screenshot.svg + telegram_assets/*.png in "
          f"{len(dirs)} folders (run_report.md next to them)")

    if failures:
        print()
        print("[!] Failures:")
        for folder, reason, excerpt in failures:
            print(f"  - {folder}: {reason}")
            for line in [ln for ln in excerpt.splitlines() if ln.strip()][:8]:
                print(f"      {line}")
        return 1

    print("[+] All examples executed successfully; logs, reports and screenshots are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
