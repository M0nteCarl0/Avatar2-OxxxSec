#!/usr/bin/env python3
"""
Master Builder: Generates all 30 chapter folders, example.py scripts,
individual README.md files, master avatar2_telegram_posts_series.md,
and the comprehensive root README.md.
"""

import ast
import os
import re
import sys

from generate_posts_data import POSTS_1_TO_15
from generate_posts_data_2 import POSTS_16_TO_30
from generate_posts_compact import POST_CODE

ALL_POSTS = POSTS_1_TO_15 + POSTS_16_TO_30
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Publication link injected into every post (README + Telegram series)
REPO_URL = "https://github.com/M0nteCarl0/Avatar2-OxxxSec"
REPO_LABEL = ("Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and "
              "dynamic-analysis playbook")

print(f"[*] Total posts to generate: {len(ALL_POSTS)}")

def format_post_markdown(post: dict, is_standalone: bool = True) -> str:
    md = []
    if is_standalone:
        md.append(f"# {post['emoji']} {post['title']} with Avatar2 Framework (Python practice)\n")
    else:
        md.append(f"## 📌 Post {post['num']:02d} | {post['emoji']} {post['title']} with Avatar2 Framework (Python practice)\n")

    md.append(f"{post['intro']}\n")
    
    md.append("## 🧠 Core Concept")
    for concept in post["core_concepts"]:
        md.append(f"- {concept}")
    md.append("")
    
    md.append("## 💻 Implementation Example")
    md.append("```python")
    md.append(post["code"].strip())
    md.append("```\n")

    md.append("## 🔥 Use Cases")
    for uc in post["use_cases"]:
        md.append(f"- {uc}")
    md.append("")
    
    md.append("## ⚠️ Caveats & Responsible Practice")
    for cav in post["caveats"]:
        md.append(f"- {cav}")
    md.append("")
    
    md.append("## 📦 Test Data & Sample Binaries / Targets")
    md.append(f"{post['test_data']}\n")
    
    md.append("## 🔗 Resources")
    for res in post["resources"]:
        md.append(f"- {res}")
    if is_standalone:
        md.append(f"- **Full repository**: [{REPO_LABEL}]({REPO_URL}) — this chapter's sources, "
                  f"run log, report and execution screenshot.")
    md.append("")

    if not is_standalone:
        md.append("## 📸 Real Execution Capture")
        md.append(f"![Real execution of {post['dir_name']}](telegram_assets/{post['dir_name']}.png)")
        md.append("")
        md.append(f"**📦 Source, run log & report**: [{REPO_LABEL}: {post['dir_name']}]"
                  f"({REPO_URL}/tree/main/{post['dir_name']})")
        md.append("")

    md.append(" ".join(post["hashtags"]))
    md.append("")
    return "\n".join(md)


# ------------------------------------------------------------------------------
# Telegram-ready chapter posts (OxxxSecQuling house style)
#
# One Telegram text message is limited to 4096 UTF-16 code units (every emoji
# costs two), so posts 05..30 are published as a compact version of the same
# structure: title, intro, Core Concept, Implementation Example (the shortened
# script from generate_posts_compact.py), Use Cases, Caveats, Test Data,
# Resources and hashtags. The full reference implementation stays in example.py.
# ------------------------------------------------------------------------------

TELEGRAM_MESSAGE_LIMIT = 4096   # hard limit of a single Telegram text message
TELEGRAM_SAFE_UNITS = 4064      # 32 units below the hard limit for safety


def telegram_units(text: str) -> int:
    """Telegram measures message length in UTF-16 code units (emoji count twice)."""
    return len(text.encode("utf-16-le")) // 2


def _flat(text: str) -> str:
    return " ".join(str(text).split())


def _clip(text: str, limit: int) -> str:
    """Collapse whitespace and cut on a word boundary, keeping a visible ellipsis."""
    text = _flat(text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-") + "…"


def _lead_sentences(text: str, limit: int) -> str:
    """First whole sentences of an intro, capped at `limit` characters."""
    text = _flat(text)
    if len(text) <= limit:
        return text
    kept = ""
    for sentence in re.split(r"(?<=[.!?]) ", text):
        candidate = (kept + " " + sentence).strip()
        if kept and len(candidate) > limit:
            break
        kept = candidate
    return kept if kept else _clip(text, limit)


# Progressively leaner budgets: the first profile that fits the message wins.
# Whole bullets/sections are dropped instead of truncating sentences, so every
# published post still reads like prose.
_POST_PROFILES = (
    dict(concepts=5, use_cases=5, caveats=4, resources=3, intro=430, item=150),
    dict(concepts=5, use_cases=4, caveats=4, resources=3, intro=400, item=150),
    dict(concepts=4, use_cases=4, caveats=3, resources=3, intro=360, item=150),
    dict(concepts=4, use_cases=4, caveats=3, resources=2, intro=320, item=150),
    dict(concepts=4, use_cases=3, caveats=3, resources=2, intro=290, item=150),
    dict(concepts=3, use_cases=3, caveats=2, resources=2, intro=260, item=150),
    dict(concepts=3, use_cases=3, caveats=2, resources=1, intro=230, item=150),
    dict(concepts=3, use_cases=2, caveats=2, resources=1, intro=200, item=150),
    dict(concepts=3, use_cases=2, caveats=2, resources=0, intro=180, item=150),
    dict(concepts=2, use_cases=2, caveats=1, resources=0, intro=180, item=150),
)


# Standard "🔗 Resources" block of every chapter post (same in all 26 posts).
POST_RESOURCES = (
    "- Avatar2 Official Repository (https://github.com/avatartwo/avatar2)",
    "- Avatar2 Documentation (https://avatar2.readthedocs.io/en/latest/)",
    "- Avatar2 Research Paper - EURECOM (https://s3.eurecom.fr/docs/bar18_avatar2.pdf)",
    "- Full repository: Avatar2-OxxxSec - 30-chapter Avatar2 firmware orchestration and "
    "dynamic-analysis playbook — this chapter's sources, run log, report and execution "
    "screenshot.",
)


def _render_telegram_post(post: dict, profile: dict) -> str:
    md = [f"# {post['emoji']} {post['title']} (Python practice)",
          "",
          _lead_sentences(post["intro"], profile["intro"]),
          "",
          "## 🧠 Core Concept"]
    md.extend(f"- {_clip(item, profile['item'])}" for item in post["core_concepts"][:profile["concepts"]])
    md.extend(["", "## 💻 Implementation Example", "```python",
               POST_CODE.get(post["num"], "").strip(), "```", "",
               "## 🔥 Use Cases"])
    md.extend(f"- {_clip(item, profile['item'])}" for item in post["use_cases"][:profile["use_cases"]])
    md.extend(["", "## ⚠️ Caveats & Responsible Practice"])
    md.extend(f"- {_clip(item, profile['item'] + 15)}" for item in post["caveats"][:profile["caveats"]])
    md.extend(["", "## 📦 Test Data & Sample Binaries"])
    md.extend(_clip(line, profile["item"] + 15)
              for line in post["test_data"].splitlines() if line.strip())
    md.extend(["", "## 🔗 Resources"])
    md.extend(POST_RESOURCES)
    md.extend(["", " ".join(post["hashtags"]), ""])
    return "\n".join(md)


def format_telegram_readme(post: dict) -> str:
    """Chapter README that always fits into a single Telegram text message."""
    text = ""
    for profile in _POST_PROFILES:
        text = _render_telegram_post(post, profile)
        if telegram_units(text) <= TELEGRAM_SAFE_UNITS:
            return text
    return text


def build_root_readme(posts: list) -> str:
    lines = [
        "# ⚡️ Avatar2 Framework: Advanced Multi-Target Firmware Orchestration Playbook",
        "",
        "[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)",
        "[![Avatar2 Framework](https://img.shields.io/badge/Avatar2-1.4.7-green.svg)](https://github.com/avatartwo/avatar2)",
        "[![Cross-Target](https://img.shields.io/badge/Targets-QEMU%20%7C%20Unicorn%20%7C%20OpenOCD%20%7C%20GDB%20%7C%20PANDA%20%7C%20angr-orange.svg)](https://github.com/avatartwo/avatar2)",
        "[![HITL](https://img.shields.io/badge/Hardware--in--the--Loop-JTAG%20%7C%20SWD%20%7C%20Memory--Forwarding-purple.svg)](https://github.com/avatartwo/avatar2)",
        "[![Telegram Channel](https://img.shields.io/badge/Telegram-OxxxSec-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/OxxxSec)",
        "[![Tests Passing](https://img.shields.io/badge/tests-30%2F30%20passed-brightgreen.svg)](verify_all.py)",
        "",
        "A comprehensive, publication-ready technical playbook and **30-part Telegram post series** exploring practical embedded firmware dynamic analysis, hardware-in-the-loop (HITL) memory forwarding, peripheral modeling, vulnerability research, and automated security triage using the [Avatar2 Framework](https://github.com/avatartwo/avatar2).",
        "",
        "> 📢 **Telegram Channel**: Follow [@OxxxSec](https://t.me/OxxxSec) for cutting-edge binary analysis, firmware security, and reverse engineering playbooks!",
        "",
        "---",
        "",
        "## 📑 Table of Contents (30-Part Master Series)",
        "",
        "| # | Topic & Directory | Core Emulation / Analysis Focus |",
        "|:---:|:---|:---|"
    ]
    
    for p in posts:
        num_str = f"**{p['num']:02d}**"
        dir_link = f"[{p['dir_name']}]({p['dir_name']}/)"
        focus = p["title"]
        lines.append(f"| {num_str} | {dir_link} | {focus} |")
        
    lines.extend([
        "",
        "---",
        "",
        "## 🏗 Architectural Overview: Avatar2 Multi-Target Ecosystem",
        "",
        "```mermaid",
        "flowchart TD",
        "    subgraph Orchestrator[\"Avatar2 Core Orchestrator (Python)\"]",
        "        AV[\"avatar2.Avatar (Central Hub)\"]",
        "        IT[\"IntervalTree Memory Manager\"]",
        "        WM[\"Watchmen Event Subsystem\"]",
        "        FQ[\"Fast Queue Message Dispatcher\"]",
        "    end",
        "",
        "    subgraph Targets[\"Heterogeneous Execution Targets\"]",
        "        QEMU[\"QemuTarget (Full System)\"]",
        "        UC[\"UnicornTarget (Fast JIT CPU)\"]",
        "        OOCD[\"OpenOCDTarget (JTAG / SWD Silicon)\"]",
        "        JL[\"JLinkTarget (SEGGER High-Speed)\"]",
        "        ANGR[\"angr (Symbolic Execution)\"]",
        "        PANDA[\"PandaTarget (Record & Replay)\"]",
        "        DUMMY[\"DummyTarget (Mock / Unit-Testing)\"]",
        "    end",
        "",
        "    subgraph Peripherals[\"Virtual & Forwarded Peripherals\"]",
        "        MF[\"Memory Forwarding Engine (HITL)\"]",
        "        UART[\"Virtual UART (PL011 / USART)\"]",
        "        WDT[\"Hardware Watchdog Timer\"]",
        "        AES[\"Hardware AES / Crypto Engine\"]",
        "        DMA[\"Direct Memory Access Controller\"]",
        "        SPI[\"SPI Flash & Sensor Buses\"]",
        "    end",
        "",
        "    AV --> IT",
        "    AV --> WM",
        "    AV --> FQ",
        "    AV --> Targets",
        "    IT --> MF",
        "    MF --> Peripherals",
        "    Targets <--> MF",
        "```",
        "",
        "---",
        "",
        "## 🚀 Quick Start",
        "",
        "### 1. Automated Environment Setup",
        "",
        "Use the bootstrap script for your platform:",
        "",
        "#### Windows PowerShell:",
        "```powershell",
        "powershell -ExecutionPolicy Bypass -File .\\setup_env.ps1",
        "```",
        "",
        "#### Windows Command Prompt (CMD):",
        "```cmd",
        "setup_env.bat",
        "```",
        "",
        "#### Linux / macOS / WSL:",
        "```bash",
        "chmod +x setup_env.sh",
        "./setup_env.sh",
        "```",
        "",
        "---",
        "",
        "### 2. Manual Environment Setup",
        "",
        "```bash",
        "# 1. Create virtual environment",
        "python -m venv .venv",
        "",
        "# 2. Activate virtual environment",
        "# Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1",
        "# Windows CMD: .\\.venv\\Scripts\\activate.bat",
        "# Linux / WSL: source .venv/bin/activate",
        "",
        "# 3. Upgrade pip and setuptools",
        "pip install --upgrade pip \"setuptools<70\" wheel",
        "",
        "# 4. Install dependencies",
        "pip install -r requirements.txt",
        "",
        "# 5. Verify all 30 chapters",
        "python verify_all.py",
        "```",
        "",
        "---",
        "",
        "### 3. Running All 30 Examples & Generating Logs",
        "",
        "To execute all 30 post examples sequentially, capture the real stdout/stderr of every example and print a",
        "summary table:",
        "",
        "```bash",
        "python run_all_and_log.py",
        "```",
        "",
        "Each run writes three artifacts into every post folder:",
        "",
        "| Artifact | Content |",
        "|:--|:--|",
        "| `<post>/run.log` | The untouched stdout (plus a `--- STDERR ---` section when the example wrote to stderr) |",
        "| `<post>/run_report.md` | Markdown report: status table (exit code, duration, output size) + the captured output |",
        "| `<post>/run_screenshot.svg` | Terminal-style screenshot of the real execution (renders inline on GitHub) |",
        "",
        "Every post folder also ships its own launchers, so a single example can be started without touching the",
        "repository root:",
        "",
        "| Launcher | Platform |",
        "|:--|:--|",
        "| `<post>/run.sh` | Linux / macOS / WSL (`./run.sh`) |",
        "| `<post>/run.ps1` | Windows PowerShell (`.\\run.ps1`) |",
        "",
        "Telegram-ready captures are exported to `telegram_assets/<post>.png` (one raster screenshot per",
        "chapter, referenced from the Telegram series below). PNG export needs `pillow`; when it is not",
        "installed the runner simply skips the PNG step and keeps the SVG screenshots.",
        "",
        "---",
        "",
        "## 📱 Telegram Series Publication",
        "",
        "Chapters **05–30** ship a `README.md` that **is** the Telegram post: it keeps the house structure",
        "(`# <emoji> <title> (Python practice)` → intro → Core Concept → Implementation Example → Use Cases",
        "→ Caveats & Responsible Practice → Test Data → Resources → hashtags) and stays below the",
        "4096 UTF-16 code units of a single Telegram message, with the shortened implementation example",
        "inlined. The `🔗 Resources` block is identical in every post (Avatar2 repository, docs, the",
        "EURECOM paper and the link to this repository). The full, hand-tested reference script of a",
        "chapter stays in its `example.py`; `verify_all.py` re-checks the message budget of every README.",
        "",
        "The long-form variants (full source embedded, better suited for a blog or a wiki page) of all",
        "30 chapters stay compiled in:",
        "- **[avatar2_telegram_posts_series.md](avatar2_telegram_posts_series.md)**",
        "",
        "Each post contains:",
        "- Catchy technical title and architectural hook",
        "- Core concept bullet points explaining the underlying hardware and framework mechanics",
        "- Complete, standalone, runnable Python implementation example",
        "- 5 real-world security engineering use cases",
        "- Critical caveats, timing rules, and responsible practice tips",
        "- Target specs and sample binary layouts",
        "- Curated community documentation and research links",
        "- Relevant Telegram discoverability hashtags",
        "",
        "---",
        "",
        "## 📜 License",
        "",
        "This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.",
        "",
        "---",
        "",
        "**Maintained by [OxxxSec](https://t.me/OxxxSec)** | Dedicated to advancing embedded firmware security and binary dynamic analysis."
    ])
    return "\n".join(lines)

def build_telegram_series_markdown(posts: list) -> str:
    lines = [
        "# 🚀 Master Avatar2 Framework: Complete 30-Post Telegram Series & Python Playbook",
        "",
        "> A comprehensive, publication-ready collection of 30 original Telegram technical posts covering the [Avatar2 Framework](https://github.com/avatartwo/avatar2) — the premier multi-target orchestration and hybrid firmware dynamic analysis platform.",
        "",
        "> Each post is structured with an architectural overview, core concepts, runnable Python code examples, real-world use cases, pro-tips & caveats, test data & sample targets, community resources, and hashtags.",
        "",
        "---",
        ""
    ]
    for p in posts:
        lines.append(format_post_markdown(p, is_standalone=False))
        lines.append("\n---\n")
    return "\n".join(lines)

RUN_SH_BODY = '''set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON_BIN="python3"
for candidate in "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/.venv/Scripts/python.exe"; do
    if [ -x "${candidate}" ]; then
        PYTHON_BIN="${candidate}"
        break
    fi
done

cd "${SCRIPT_DIR}"
exec "${PYTHON_BIN}" example.py "$@"
'''

RUN_PS1_BODY = '''#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

$PythonExe = "python"
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    $PythonExe = "python3"
}
foreach ($Candidate in @(
    (Join-Path $RepoRoot ".venv\\Scripts\\python.exe"),
    (Join-Path $RepoRoot ".venv/bin/python")
)) {
    if (Test-Path $Candidate) {
        $PythonExe = $Candidate
        break
    }
}

Push-Location $ScriptDir
try {
    & $PythonExe "example.py" @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
'''


def build_run_sh(post: dict) -> str:
    """POSIX quick launcher for one example folder."""
    header = (
        "#!/usr/bin/env bash\n"
        "# Quick launcher for post %02d: %s\n"
        "# Usage: ./run.sh   (extra arguments are forwarded to example.py)\n" % (post["num"], post["title"])
    )
    return header + RUN_SH_BODY


def build_run_ps1(post: dict) -> str:
    """PowerShell quick launcher for one example folder."""
    header = (
        "# Quick launcher for post %02d: %s\n"
        "# Usage: .\\run.ps1   (extra arguments are forwarded to example.py)\n" % (post["num"], post["title"])
    )
    return header + RUN_PS1_BODY


def main():
    print("[*] Generating all 30 chapter directories and files...")
    
    for post in ALL_POSTS:
        folder_name = post["dir_name"]
        folder_path = os.path.join(BASE_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # Write example.py
        example_path = os.path.join(folder_path, "example.py")
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(post["code"].strip() + "\n")
            
        # Write individual README.md: post 01..04 keep the long form, 05..30 are
        # published as a Telegram-sized post (see format_telegram_readme).
        readme_path = os.path.join(folder_path, "README.md")
        if post["num"] in POST_CODE:
            readme_text = format_telegram_readme(post)
            readme_units = telegram_units(readme_text)
            if readme_units > TELEGRAM_MESSAGE_LIMIT:
                raise SystemExit(f"Post {post['num']:02d}: README is {readme_units} UTF-16 units, "
                                 f"above the {TELEGRAM_MESSAGE_LIMIT}-unit Telegram limit")
        else:
            readme_text = format_post_markdown(post, is_standalone=True)
            readme_units = telegram_units(readme_text)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_text)

        # Write quick launchers (Bash + PowerShell)
        sh_path = os.path.join(folder_path, "run.sh")
        with open(sh_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(build_run_sh(post))
        ps1_path = os.path.join(folder_path, "run.ps1")
        with open(ps1_path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(build_run_ps1(post))

        print(f"  [+] Post {post['num']:02d}: Created {folder_name} "
              f"(example.py, README.md, run.sh, run.ps1)")
        
    # Generate master telegram series markdown
    print("[*] Generating master avatar2_telegram_posts_series.md...")
    tg_series_path = os.path.join(BASE_DIR, "avatar2_telegram_posts_series.md")
    with open(tg_series_path, "w", encoding="utf-8") as f:
        f.write(build_telegram_series_markdown(ALL_POSTS))
    print(f"  [+] Written {os.path.getsize(tg_series_path)} bytes to {os.path.basename(tg_series_path)}")
    
    # Generate root README.md
    print("[*] Generating root README.md...")
    root_readme_path = os.path.join(BASE_DIR, "README.md")
    with open(root_readme_path, "w", encoding="utf-8") as f:
        f.write(build_root_readme(ALL_POSTS))
    print(f"  [+] Written {os.path.getsize(root_readme_path)} bytes to {os.path.basename(root_readme_path)}")
    
    print("\n[SUCCESS] All 30 posts, directories, and documentation successfully generated!")

if __name__ == "__main__":
    main()
