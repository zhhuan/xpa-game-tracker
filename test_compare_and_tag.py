#!/usr/bin/env python3
"""Regression tests for persistent XPA first-seen timestamps."""

import unittest

from compare_and_tag_new_games_updated import tag_new_games


class TagNewGamesTests(unittest.TestCase):
    def test_keeps_old_timestamp_and_dates_only_new_game(self):
        old_time = "2026-10-17T03:17:00+00:00"
        new_time = "2026-10-18T03:17:00+00:00"
        current = [
            {"productId": "old", "title": "Old game", "releaseDate": "2025-01-01"},
            {"productId": "new", "title": "New game", "releaseDate": "2026-01-01"},
        ]
        previous = [current[0]]
        published = [{**current[0], "firstSeenDate": old_time, "isNew": True}]

        tagged, new_games = tag_new_games(current, previous, published, now=new_time)

        by_id = {game["productId"]: game for game in tagged}
        self.assertEqual(by_id["old"]["firstSeenDate"], old_time)
        self.assertFalse(by_id["old"]["isNew"])
        self.assertEqual(by_id["new"]["firstSeenDate"], new_time)
        self.assertTrue(by_id["new"]["isNew"])
        self.assertEqual([game["productId"] for game in new_games], ["new"])

    def test_does_not_invent_timestamp_for_legacy_game(self):
        game = {"productId": "legacy", "title": "Legacy game"}

        tagged, _ = tag_new_games([game], [game], [], now="2026-10-18T03:17:00+00:00")

        self.assertNotIn("firstSeenDate", tagged[0])


if __name__ == "__main__":
    unittest.main()
