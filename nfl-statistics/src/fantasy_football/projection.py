"""Supervised veteran projection: past-seasons form -> next-season value.

Replaces the fixed recency-weighted average with a ridge regression trained
on historical season-to-season transitions. Features separate opportunity
(carries, targets, pass attempts per game) from production (fantasy PPG),
capture durability directly (games played), and include experience and
position — so the model learns its own recency weights, volume-vs-TD
regression, and position aging effects from data.

Target: next-season total fantasy points / 17 ("points per roster slot"),
which rewards per-game production AND durability in the units that win
fantasy seasons.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from fantasy_football.ml import RidgeRegression, kfold_alpha_search
from fantasy_football.scoring import ScoringRules

N_LAGS = 3
ALPHAS = [1.0, 3.0, 10.0, 30.0, 100.0]
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")


def _num(game: Dict, key: str) -> float:
    val = game.get(key, 0)
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def season_summary(log: List[Dict], position: str, rules: ScoringRules) -> Dict[str, float]:
    """Compact per-season stat summary used to build features and targets."""
    scores = rules.compute_season_scores(log, position)
    g = len(log)
    total = sum(scores)
    last8 = scores[-8:]
    tds = sum(
        _num(r, "rushing_tds") + _num(r, "receiving_tds") + _num(r, "passing_tds")
        for r in log
    )
    yds = sum(_num(r, "rushing_yards") + _num(r, "receiving_yards") for r in log)
    return {
        "games": float(g),
        "ppg": total / g if g else 0.0,
        "pts_per_slot": total / 17.0,
        "carries_pg": sum(_num(r, "carries") for r in log) / g if g else 0.0,
        "targets_pg": sum(_num(r, "targets") for r in log) / g if g else 0.0,
        "pass_att_pg": sum(_num(r, "attempts") for r in log) / g if g else 0.0,
        "last8_ppg": sum(last8) / len(last8) if last8 else 0.0,
        "td_pg": tds / g if g else 0.0,
        "scrim_yds_pg": yds / g if g else 0.0,
        "total": total,
    }


SUMMARY_FEATURES = ["games", "ppg", "pts_per_slot", "carries_pg", "targets_pg",
                    "pass_att_pg", "last8_ppg", "td_pg", "scrim_yds_pg"]

FEATURE_NAMES = (
    [f"lag{k}_{f}" for k in range(1, N_LAGS + 1) for f in ["played"] + SUMMARY_FEATURES]
    + ["experience"]
    + [f"is_{p.lower()}" for p in POSITIONS[1:]]
)


def build_summaries(
    logs_by_season: Dict[int, Dict[str, List[Dict]]],
    positions: Dict[str, str],
    rules: ScoringRules,
) -> Dict[int, Dict[str, Dict[str, float]]]:
    """{season: {player: season_summary}} for every loaded season."""
    return {
        season: {
            name: season_summary(log, positions.get(name, ""), rules)
            for name, log in logs.items()
        }
        for season, logs in logs_by_season.items()
    }


def _features_for(
    name: str,
    target_season: int,
    summaries: Dict[int, Dict[str, Dict[str, float]]],
    positions: Dict[str, str],
    first_seen: Dict[str, int],
) -> List[float]:
    feats: List[float] = []
    for lag in range(1, N_LAGS + 1):
        s = summaries.get(target_season - lag, {}).get(name)
        feats.append(1.0 if s else 0.0)
        feats.extend([s[f] for f in SUMMARY_FEATURES] if s else [0.0] * len(SUMMARY_FEATURES))
    exp = min(target_season - first_seen.get(name, target_season), 10)
    feats.append(float(exp))
    pos = positions.get(name, "")
    feats.extend(1.0 if pos == p else 0.0 for p in POSITIONS[1:])
    return feats


class VeteranProjector:
    """Ridge model over lagged season summaries.

    Usage::

        proj = VeteranProjector().fit(summaries, positions, train_targets)
        values = proj.predict_season(summaries, positions, season)
    """

    def __init__(self) -> None:
        self.model: Optional[RidgeRegression] = None
        self.alpha: float = 0.0
        self.cv_r2: float = 0.0
        self._first_seen: Dict[str, int] = {}

    def _compute_first_seen(self, summaries) -> None:
        self._first_seen = {}
        for season in sorted(summaries):
            for name in summaries[season]:
                self._first_seen.setdefault(name, season)

    def fit(
        self,
        summaries: Dict[int, Dict[str, Dict[str, float]]],
        positions: Dict[str, str],
        target_seasons: List[int],
    ) -> "VeteranProjector":
        """Train on (features from t-1..t-3 -> pts_per_slot in t) pairs.

        Only players active in season t-1 are training rows — mirroring
        prediction time, when the pool is last season's active players.
        """
        self._compute_first_seen(summaries)
        X, y = [], []
        for t in target_seasons:
            prev = summaries.get(t - 1, {})
            for name in prev:
                target = summaries.get(t, {}).get(name)
                X.append(_features_for(name, t, summaries, positions, self._first_seen))
                y.append(target["pts_per_slot"] if target else 0.0)
        self.alpha, self.cv_r2 = kfold_alpha_search(X, y, ALPHAS)
        self.model = RidgeRegression(self.alpha).fit(X, y)
        return self

    def predict_season(
        self,
        summaries: Dict[int, Dict[str, Dict[str, float]]],
        positions: Dict[str, str],
        season: int,
    ) -> Dict[str, float]:
        """Predicted pts-per-slot for every player active in season-1."""
        pool = list(summaries.get(season - 1, {}))
        X = [
            _features_for(name, season, summaries, positions, self._first_seen)
            for name in pool
        ]
        preds = self.model.predict(X)
        return {name: round(p, 4) for name, p in zip(pool, preds)}
