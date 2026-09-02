#!/usr/bin/env python3
"""Validate deployable files and XPA data invariants."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = ("index.html", "styles.css", "app.js")
DATA_FILES = (
    ROOT / "data" / "games.json",
    ROOT / "data" / "games.previous.json",
    ROOT / "data" / "games_with_new_markers.json",
)


def validate_games_file(path):
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    games = payload.get("games")
    if not isinstance(games, list) or not games:
        raise ValueError(f"{path.name}: games 必须是非空数组")

    product_ids = []
    for index, game in enumerate(games):
        if not isinstance(game, dict):
            raise ValueError(f"{path.name}: games[{index}] 不是对象")
        if not (game.get("title") or game.get("name")):
            raise ValueError(f"{path.name}: games[{index}] 缺少名称")
        if game.get("productId"):
            product_ids.append(str(game["productId"]).lower())

    if len(product_ids) != len(set(product_ids)):
        raise ValueError(f"{path.name}: productId 存在重复")
    return len(games)


def validate_published_default_order(path):
    with path.open("r", encoding="utf-8") as handle:
        games = json.load(handle)["games"]

    def group(game):
        if game.get("isNew", False):
            return 0
        if not str(game.get("releaseDate") or "").strip():
            return 1
        return 2

    groups = [group(game) for game in games]
    if groups != sorted(groups):
        raise ValueError(
            "games_with_new_markers.json 默认顺序必须为：新增、无发售日期、正常游戏"
        )


def main():
    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            raise FileNotFoundError(f"缺少发布文件: {relative_path}")

    counts = {path.name: validate_games_file(path) for path in DATA_FILES}
    current_count = counts["games.json"]
    published_count = counts["games_with_new_markers.json"]
    if current_count != published_count:
        raise ValueError("games.json 与发布版游戏数量不一致")
    validate_published_default_order(DATA_FILES[2])

    print("项目验证通过")
    for name, count in counts.items():
        print(f"- {name}: {count} 个游戏")


if __name__ == "__main__":
    main()
