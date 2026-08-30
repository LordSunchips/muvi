"""Value Over Replacement (VOR) for fantasy football.

Same idea as nba-statistics' VORCalculator: a player's value is their
risk-adjusted per-game production minus the production of the best player
expected to go undrafted at their position (the "replacement").

NFL wrinkle: FLEX spots. Replacement depth at RB/WR/TE depends on how the
league's FLEX slots get filled, so flex slots are allocated greedily to the
best remaining flex-eligible players before replacement ranks are fixed.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from fantasy_football.scoring import ScoringRules

LOGGER = logging.getLogger(__name__)

FLEX_ELIGIBLE = ("RB", "WR", "TE")


def compute_base_value(
    game_log: List[Dict],
    rules: ScoringRules,
    position: str,
    season_games: int = 17,
    risk_aversion: float = 0.1,
) -> float:
    """Risk-adjusted player value.

    base_value = avg_score * availability_factor - risk_aversion * std_dev

    availability_factor = games_played / season_games, capped at 1.0.
    Penalizes injury-prone players (low availability) and inconsistent
    players (high standard deviation).
    """
    scores = rules.compute_season_scores(game_log, position)
    if not scores:
        return 0.0
    avg = statistics.fmean(scores)
    std = statistics.stdev(scores) if len(scores) > 1 else 0.0
    availability = min(len(scores) / season_games, 1.0)
    return round(avg * availability - risk_aversion * std, 4)


def compute_weighted_base_value(
    logs_by_season: Dict[int, List[Dict]],
    rules: ScoringRules,
    position: str,
    season_games: int = 17,
    risk_aversion: float = 0.1,
    recency_decay: float = 0.5,
) -> float:
    """Recency-weighted multi-season base value.

    Each season the player actually appeared in gets its own risk-adjusted
    base value, then seasons are averaged with weights decay**seasons_ago
    (most recent season = 1.0), renormalized over the seasons present. A
    player with three seasons of data is weighted across just those three.
    """
    present = sorted((s for s, log in logs_by_season.items() if log), reverse=True)
    if not present:
        return 0.0
    latest = present[0]
    total_w = 0.0
    total = 0.0
    for season in present:
        w = recency_decay ** (latest - season)
        val = compute_base_value(
            logs_by_season[season], rules, position, season_games, risk_aversion
        )
        total += w * val
        total_w += w
    return round(total / total_w, 4)


@dataclass
class LeagueSettings:
    """Configuration for a fantasy football league.

    roster_spots counts STARTING slots per position; flex_spots counts
    FLEX (RB/WR/TE) starting slots. Bench/IR slots don't affect
    replacement level and are excluded.
    """

    num_teams: int = 12
    roster_spots: Dict[str, int] = field(
        default_factory=lambda: {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
    )
    flex_spots: int = 2
    scoring_rules: ScoringRules = field(default_factory=ScoringRules.sleeper_default)
    season_games: int = 17
    risk_aversion: float = 0.1
    recency_decay: float = 0.5  # weight = decay ** seasons_ago in multi-season averaging


class VORCalculator:
    """Computes Value Over Replacement for fantasy football players."""

    def __init__(self, settings: LeagueSettings) -> None:
        self.settings = settings

    def _build_position_pools(
        self,
        base_values: Dict[str, float],
        player_positions: Dict[str, str],
    ) -> Dict[str, List[Tuple[str, float]]]:
        """{position: [(player, base_value), ...]} sorted descending."""
        pools: Dict[str, List[Tuple[str, float]]] = {
            pos: [] for pos in self.settings.roster_spots
        }
        for name, val in base_values.items():
            pos = player_positions.get(name)
            if pos is None:
                LOGGER.warning("Player '%s' has no position — excluded.", name)
                continue
            if pos in pools:
                pools[pos].append((name, val))
        for pos in pools:
            pools[pos].sort(key=lambda x: (-x[1], x[0]))
        return pools

    def _allocate_flex_slots(
        self, pools: Dict[str, List[Tuple[str, float]]]
    ) -> Dict[str, int]:
        """Greedily assign league-wide FLEX slots to the best remaining
        flex-eligible players (after dedicated starters are removed).

        Returns {position: number_of_flex_slots_absorbed}.
        """
        n = self.settings.num_teams
        flex_total = n * self.settings.flex_spots
        candidates: List[Tuple[float, str]] = []
        for pos in FLEX_ELIGIBLE:
            start = n * self.settings.roster_spots.get(pos, 0)
            for _name, val in pools.get(pos, [])[start:]:
                candidates.append((val, pos))
        candidates.sort(key=lambda x: -x[0])
        alloc = {pos: 0 for pos in FLEX_ELIGIBLE}
        for _val, pos in candidates[:flex_total]:
            alloc[pos] += 1
        return alloc

    def compute_replacement_values(
        self,
        base_values: Dict[str, float],
        player_positions: Dict[str, str],
    ) -> Dict[str, float]:
        """Replacement-level base_value per position.

        Replacement rank = num_teams * roster_spots[pos] (+ flex slots the
        position absorbs, for RB/WR/TE). This indexes the first player
        projected NOT to be drafted as a starter at that position.
        """
        pools = self._build_position_pools(base_values, player_positions)
        flex_alloc = self._allocate_flex_slots(pools)
        replacement: Dict[str, float] = {}
        for pos, spots in self.settings.roster_spots.items():
            pool = pools.get(pos, [])
            if not pool:
                LOGGER.warning("No players at position '%s' — replacement 0.0.", pos)
                replacement[pos] = 0.0
                continue
            idx = self.settings.num_teams * spots + flex_alloc.get(pos, 0)
            idx = min(idx, len(pool) - 1)
            replacement[pos] = pool[idx][1]
        return replacement

    def compute_vor(
        self,
        base_values: Dict[str, float],
        replacement_values: Dict[str, float],
        player_positions: Dict[str, str],
    ) -> Dict[str, float]:
        """VOR = base_value - replacement_value at the player's position."""
        vor: Dict[str, float] = {}
        for name, val in base_values.items():
            pos = player_positions.get(name)
            if pos is None or pos not in replacement_values:
                vor[name] = 0.0
                continue
            vor[name] = round(val - replacement_values[pos], 4)
        return vor
