#!/usr/bin/env python3
"""Run the complete, repeatable XPA data update pipeline."""

import shutil
import subprocess
import sys
import os
from pathlib import Path


DATA_DIR = Path("data")
CURRENT_FILE = DATA_DIR / "games.json"
PREVIOUS_FILE = DATA_DIR / "games.previous.json"


def run(script):
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    subprocess.run([sys.executable, script], check=True, env=environment)


def main():
    if not CURRENT_FILE.exists():
        raise FileNotFoundError(f"缺少基准数据文件: {CURRENT_FILE}")

    DATA_DIR.mkdir(exist_ok=True)
    shutil.copy2(CURRENT_FILE, PREVIOUS_FILE)
    run("xpa_api_fetcher_with_date.py")
    run("compare_and_tag_new_games_updated.py")
    run("validate_project.py")


if __name__ == "__main__":
    main()
