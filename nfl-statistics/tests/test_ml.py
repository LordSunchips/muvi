import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fantasy_football.ml import RidgeRegression, kfold_alpha_search, r_squared, spearman


class TestRidge(unittest.TestCase):
    def test_recovers_linear_relationship(self):
        rng = random.Random(7)
        X = [[rng.uniform(0, 10), rng.uniform(0, 5)] for _ in range(200)]
        y = [3.0 * a - 2.0 * b + 1.0 + rng.gauss(0, 0.01) for a, b in X]
        model = RidgeRegression(alpha=1e-6).fit(X, y)
        pred = model.predict([[2.0, 1.0]])[0]
        self.assertAlmostEqual(pred, 3.0 * 2 - 2.0 * 1 + 1.0, places=1)

    def test_r_squared_perfect_and_mean(self):
        y = [1.0, 2.0, 3.0]
        self.assertAlmostEqual(r_squared(y, y), 1.0)
        self.assertAlmostEqual(r_squared(y, [2.0, 2.0, 2.0]), 0.0)

    def test_spearman_monotonic(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1.0)

    def test_alpha_search_returns_candidate(self):
        rng = random.Random(1)
        X = [[rng.uniform(0, 1)] for _ in range(50)]
        y = [2 * row[0] + rng.gauss(0, 0.1) for row in X]
        alpha, score = kfold_alpha_search(X, y, [0.1, 1.0, 10.0])
        self.assertIn(alpha, [0.1, 1.0, 10.0])
        self.assertGreater(score, 0.5)


class TestCollegeHelpers(unittest.TestCase):
    def test_normalize_name(self):
        from fantasy_football.college import normalize_name
        self.assertEqual(normalize_name("Marvin Harrison Jr."), "marvin harrison")
        self.assertEqual(normalize_name("A.J. Brown"), "aj brown")


if __name__ == "__main__":
    unittest.main()
