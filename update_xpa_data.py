#!/usr/bin/env python3
"""Run the complete, repeatable XPA data update pipeline."""

import json
import shutil
import subprocess
import sys
import os
from pathlib import Path


DATA_DIR = Path("data")
CURRENT_FILE = DATA_DIR / "games.json"
PREVIOUS_FILE = DATA_DIR / "games.previous.json"
PREVIOUS_BACKUP_FILE = DATA_DIR / "games.previous.json.tmp"


def run(script):
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    subprocess.run([sys.executable, script], check=True, env=environment)


def load_games(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)["games"]


def catalogs_match(first_path, second_path):
    first = json.dumps(load_games(first_path), ensure_ascii=False, sort_keys=True)
    second = json.dumps(load_games(second_path), ensure_ascii=False, sort_keys=True)
    return first == second


def main():
    if not CURRENT_FILE.exists():
        raise FileNotFoundError(f"缺少基准数据文件: {CURRENT_FILE}")

    DATA_DIR.mkdir(exist_ok=True)
    had_previous = PREVIOUS_FILE.exists()
    if had_previous:
        shutil.copy2(PREVIOUS_FILE, PREVIOUS_BACKUP_FILE)
    shutil.copy2(CURRENT_FILE, PREVIOUS_FILE)

    try:
        run("xpa_api_fetcher_with_date.py")
        if catalogs_match(CURRENT_FILE, PREVIOUS_FILE):
            # Restore byte-identical snapshots so timestamps alone never create commits.
            shutil.copy2(PREVIOUS_FILE, CURRENT_FILE)
            if had_previous:
                shutil.copy2(PREVIOUS_BACKUP_FILE, PREVIOUS_FILE)
            print("游戏目录没有变化，保留现有发布数据")
        else:
            run("compare_and_tag_new_games_updated.py")
        run("validate_project.py")
    except Exception:
        # A failed fetch must not alter either committed snapshot.
        shutil.copy2(PREVIOUS_FILE, CURRENT_FILE)
        if had_previous:
            shutil.copy2(PREVIOUS_BACKUP_FILE, PREVIOUS_FILE)
        raise
    finally:
        PREVIOUS_BACKUP_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
