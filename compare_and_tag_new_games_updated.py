#!/usr/bin/env python3
"""Compare the current and previous XPA snapshots and mark newly seen games."""

import json
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path("data")
CURRENT_FILE = DATA_DIR / "games.json"
PREVIOUS_FILE = DATA_DIR / "games.previous.json"
OUTPUT_FILE = DATA_DIR / "games_with_new_markers.json"


def load_snapshot(path):
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    games = payload.get("games")
    if not isinstance(games, list):
        raise ValueError(f"{path} 缺少 games 数组")
    return games


def game_key(game):
    product_id = str(game.get("productId") or "").strip().lower()
    if product_id:
        return f"id:{product_id}"
    title = str(game.get("title") or game.get("name") or "").strip().lower()
    return f"title:{title}" if title else None


def tag_new_games(current_games, previous_games):
    previous_by_key = {
        key: game for game in previous_games if (key := game_key(game)) is not None
    }
    tagged_games = []
    new_games = []
    now = datetime.now(timezone.utc).isoformat()

    for source_game in current_games:
        game = dict(source_game)
        key = game_key(game)
        previous_game = previous_by_key.get(key) if key else None
        is_new = previous_game is None
        game["isNew"] = is_new

        if is_new:
            game["firstSeenDate"] = now
            new_games.append(game)
        elif previous_game and previous_game.get("firstSeenDate"):
            game["firstSeenDate"] = previous_game["firstSeenDate"]
        else:
            game.pop("firstSeenDate", None)

        tagged_games.append(game)

    def default_group(game):
        if game.get("isNew", False):
            return 0
        if not str(game.get("releaseDate") or "").strip():
            return 1
        return 2

    # Python 的排序是稳定的：依次放置新增、无发售日期、正常游戏，
    # 同组内不改变 Xbox API 返回的相对顺序。
    tagged_games.sort(key=default_group)
    return tagged_games, new_games


def main():
    current_games = load_snapshot(CURRENT_FILE)
    previous_games = load_snapshot(PREVIOUS_FILE)
    tagged_games, new_games = tag_new_games(current_games, previous_games)

    payload = {
        "totalGames": len(tagged_games),
        "newGamesCount": len(new_games),
        "taggingDate": datetime.now(timezone.utc).isoformat(),
        "games": tagged_games,
    }
    temporary_file = OUTPUT_FILE.with_suffix(".json.tmp")
    with temporary_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temporary_file.replace(OUTPUT_FILE)

    print(f"当前游戏: {len(current_games)}")
    print(f"上一版游戏: {len(previous_games)}")
    print(f"新增游戏: {len(new_games)}")
    print(f"已写入: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
