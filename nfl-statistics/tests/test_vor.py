import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fantasy_football.scoring import ScoringRules
from fantasy_football.vor import LeagueSettings, VORCalculator, compute_base_value


def _settings(num_teams=2):
    return LeagueSettings(
        num_teams=num_teams,
        roster_spots={"QB": 1, "RB": 1, "WR": 1, "TE": 1, "K": 1, "DEF": 1},
        flex_spots=1,
        scoring_rules=ScoringRules.sleeper_default(),
    )


class TestBaseValue(unittest.TestCase):
    def test_availability_penalty(self):
        rules = ScoringRules.sleeper_default()
        full = [{"rushing_yards": 100} for _ in range(17)]
        half = [{"rushing_yards": 100} for _ in range(8)]
        # identical per-game output, fewer games -> lower base value
        self.assertGreater(
            compute_base_value(full, rules, "RB"),
            compute_base_value(half, rules, "RB"),
        )

    def test_consistency_penalty(self):
        rules = ScoringRules.sleeper_default()
        steady = [{"rushing_yards": 100} for _ in range(17)]
        boom_bust = [{"rushing_yards": 200 if i % 2 else 0} for i in range(17)]
        self.assertGreater(
            compute_base_value(steady, rules, "RB"),
            compute_base_value(boom_bust, rules, "RB"),
        )

    def test_empty_log(self):
        self.assertEqual(compute_base_value([], ScoringRules.sleeper_default(), "RB"), 0.0)


class TestVORCalculator(unittest.TestCase):
    def test_replacement_and_vor(self):
        calc = VORCalculator(_settings(num_teams=2))
        base = {"RB1": 20.0, "RB2": 15.0, "RB3": 10.0, "RB4": 5.0}
        positions = {n: "RB" for n in base}
        # 2 teams x 1 RB spot = 2 starters; flex alloc pulls RB3 too -> replacement is RB4
        repl = calc.compute_replacement_values(base, positions)
        self.assertEqual(repl["RB"], 5.0)
        vor = calc.compute_vor(base, repl, positions)
        self.assertEqual(vor["RB1"], 15.0)
        self.assertEqual(vor["RB4"], 0.0)

    def test_flex_allocation_prefers_best_remaining(self):
        calc = VORCalculator(_settings(num_teams=1))
        pools = calc._build_position_pools(
            {"RB1": 20.0, "RB2": 18.0, "WR1": 19.0, "WR2": 10.0, "TE1": 8.0, "TE2": 2.0},
            {"RB1": "RB", "RB2": "RB", "WR1": "WR", "WR2": "WR", "TE1": "TE", "TE2": "TE"},
        )
        # After 1 starter each, remaining best are RB2 (18), WR2 (10), TE2 (2).
        # One flex slot -> RB absorbs it.
        alloc = calc._allocate_flex_slots(pools)
        self.assertEqual(alloc, {"RB": 1, "WR": 0, "TE": 0})

    def test_small_pool_clamps_to_last_player(self):
        calc = VORCalculator(_settings(num_teams=2))
        base = {"K1": 8.0}
        repl = calc.compute_replacement_values(base, {"K1": "K"})
        self.assertEqual(repl["K"], 8.0)


if __name__ == "__main__":
    unittest.main()


class TestWeightedBaseValue(unittest.TestCase):
    def _log(self, yards, n=17):
        return [{"rushing_yards": yards} for _ in range(n)]

    def test_recency_bias(self):
        from fantasy_football.vor import compute_weighted_base_value
        rules = ScoringRules.sleeper_default()
        # improving player vs declining player, same season values reversed
        improving = {2023: self._log(50), 2024: self._log(100), 2025: self._log(150)}
        declining = {2023: self._log(150), 2024: self._log(100), 2025: self._log(50)}
        self.assertGreater(
            compute_weighted_base_value(improving, rules, "RB", recency_decay=0.7),
            compute_weighted_base_value(declining, rules, "RB", recency_decay=0.7),
        )

    def test_weights_renormalized_for_short_history(self):
        from fantasy_football.vor import compute_base_value, compute_weighted_base_value
        rules = ScoringRules.sleeper_default()
        # a rookie with one steady season gets exactly that season's base value
        one = {2025: self._log(100)}
        self.assertAlmostEqual(
            compute_weighted_base_value(one, rules, "RB"),
            compute_base_value(self._log(100), rules, "RB"),
            places=3,
        )

    def test_flat_average_when_decay_is_one(self):
        from fantasy_football.vor import compute_base_value, compute_weighted_base_value
        rules = ScoringRules.sleeper_default()
        logs = {2024: self._log(50), 2025: self._log(150)}
        expected = (
            compute_base_value(self._log(50), rules, "RB")
            + compute_base_value(self._log(150), rules, "RB")
        ) / 2
        self.assertAlmostEqual(
            compute_weighted_base_value(logs, rules, "RB", recency_decay=1.0),
            expected,
            places=3,
        )

    def test_empty(self):
        from fantasy_football.vor import compute_weighted_base_value
        self.assertEqual(
            compute_weighted_base_value({}, ScoringRules.sleeper_default(), "RB"), 0.0
        )
