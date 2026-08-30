import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fantasy_football.projection import VeteranProjector, build_summaries, season_summary
from fantasy_football.scoring import ScoringRules


def _log(yards, n=17):
    return [{"rushing_yards": yards, "carries": 15} for _ in range(n)]


class TestSeasonSummary(unittest.TestCase):
    def test_summary_fields(self):
        rules = ScoringRules.sleeper_default()
        s = season_summary(_log(100, n=10), "RB", rules)
        self.assertEqual(s["games"], 10.0)
        self.assertAlmostEqual(s["ppg"], 10.0)
        self.assertAlmostEqual(s["pts_per_slot"], 100 / 17.0, places=3)
        self.assertAlmostEqual(s["carries_pg"], 15.0)
        self.assertAlmostEqual(s["scrim_yds_pg"], 100.0)

    def test_empty_log(self):
        s = season_summary([], "RB", ScoringRules.sleeper_default())
        self.assertEqual(s["games"], 0.0)
        self.assertEqual(s["ppg"], 0.0)


class TestVeteranProjector(unittest.TestCase):
    def test_learns_persistence(self):
        rules = ScoringRules.sleeper_default()
        positions = {}
        logs_by_season = {}
        # 30 synthetic players with stable production across 5 seasons
        for season in range(2018, 2023):
            logs_by_season[season] = {}
            for i in range(30):
                name = f"P{i}"
                positions[name] = "RB"
                logs_by_season[season][name] = _log(30 + 5 * i)
        summaries = build_summaries(logs_by_season, positions, rules)
        proj = VeteranProjector().fit(summaries, positions, [2020, 2021, 2022])
        preds = proj.predict_season(summaries, positions, 2023)
        # stable players: predictions should preserve ordering
        self.assertGreater(preds["P29"], preds["P15"])
        self.assertGreater(preds["P15"], preds["P0"])
        # and be near their established per-slot value
        expected = summaries[2022]["P29"]["pts_per_slot"]
        self.assertAlmostEqual(preds["P29"], expected, delta=expected * 0.25)


if __name__ == "__main__":
    unittest.main()
