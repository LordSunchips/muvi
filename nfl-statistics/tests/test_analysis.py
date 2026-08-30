import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fantasy_football.analysis import generate_draft_order, write_draft_order_csv
from fantasy_football.scoring import ScoringRules
from fantasy_football.vor import LeagueSettings


class TestGenerateDraftOrder(unittest.TestCase):
    def test_ranking_and_csv(self):
        logs = {
            "Star RB": [{"rushing_yards": 150, "rushing_tds": 1} for _ in range(17)],
            "Ok RB": [{"rushing_yards": 60} for _ in range(17)],
            "Star WR": [{"receptions": 8, "receiving_yards": 110} for _ in range(17)],
        }
        positions = {"Star RB": "RB", "Ok RB": "RB", "Star WR": "WR"}
        settings = LeagueSettings(
            num_teams=1,
            roster_spots={"RB": 1, "WR": 1},
            flex_spots=0,
            scoring_rules=ScoringRules.sleeper_default(),
        )
        rows = generate_draft_order(logs, positions, settings, {"Star RB": "SF"})
        self.assertEqual(rows[0]["player"], "Star RB")
        self.assertEqual(rows[0]["overall_rank"], 1)
        self.assertEqual(rows[0]["position_rank"], 1)
        self.assertEqual(rows[0]["team"], "SF")
        ranks = [r["overall_rank"] for r in rows]
        self.assertEqual(ranks, sorted(ranks))

        with tempfile.TemporaryDirectory() as td:
            out = write_draft_order_csv(rows, Path(td) / "out.csv")
            with open(out) as fh:
                read = list(csv.DictReader(fh))
            self.assertEqual(len(read), 3)
            self.assertEqual(read[0]["player"], "Star RB")


if __name__ == "__main__":
    unittest.main()
