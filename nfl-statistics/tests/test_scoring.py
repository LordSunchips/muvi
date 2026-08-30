import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fantasy_football.scoring import ScoringRules


class TestSleeperScoring(unittest.TestCase):
    def setUp(self):
        self.rules = ScoringRules.sleeper_default()

    def test_offense_score(self):
        game = {
            "passing_yards": 300, "passing_tds": 2, "passing_interceptions": 1,
            "rushing_yards": 20, "rushing_tds": 1,
            "receptions": 4, "receiving_yards": 50, "receiving_tds": 0,
            "fumbles_lost_total": 1,
        }
        # 12 + 8 - 1 + 2 + 6 + 2 + 5 + 0 - 2 = 32
        self.assertAlmostEqual(self.rules.compute_offense_score(game), 32.0)

    def test_kicker_score(self):
        game = {
            "fg_made_30_39": 1, "fg_made_40_49": 1, "fg_made_50_59": 1,
            "fg_missed": 1, "pat_made": 3, "pat_missed": 1,
        }
        # 3 + 4 + 5 - 1 + 3 - 1 = 13
        self.assertAlmostEqual(self.rules.compute_kicker_score(game), 13.0)

    def test_points_allowed_tiers(self):
        expected = {0: 10, 3: 7, 6: 7, 10: 4, 17: 1, 24: 0, 30: -1, 35: -4, 50: -4}
        for pa, pts in expected.items():
            self.assertAlmostEqual(self.rules.points_allowed_score(pa), pts, msg=f"PA={pa}")

    def test_dst_score(self):
        game = {
            "def_sacks": 3, "def_interceptions": 2, "fumble_recovery_opp": 1,
            "def_tds": 1, "def_safeties": 0, "def_punt_blocks": 1,
            "points_allowed": 13,
        }
        # 3 + 4 + 2 + 6 + 0 + 2 + 4 = 21
        self.assertAlmostEqual(self.rules.compute_dst_score(game), 21.0)

    def test_blank_values_treated_as_zero(self):
        self.assertAlmostEqual(self.rules.compute_offense_score({"passing_yards": ""}), 0.0)


if __name__ == "__main__":
    unittest.main()
