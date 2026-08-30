"""Fantasy football scoring rules.

Mirrors the design of nba-statistics' ScoringRules: a dataclass of linear
multipliers plus non-linear pieces (kicker distance tiers, DEF points-allowed
tiers), with a preset for the Sleeper default scoring configuration.

Game rows are plain dicts keyed by nflverse column names (see data.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


def _num(game: Dict, key: str) -> float:
    """Read a numeric stat from a game row, treating blanks/NA as 0."""
    val = game.get(key, 0)
    if val in ("", "NA", None):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class ScoringRules:
    """Encapsulates a fantasy league's scoring configuration.

    Usage::

        rules = ScoringRules.sleeper_default()
        pts = rules.compute_offense_score(game_row)
    """

    # --- Offense ---
    pass_yd: float = 0.04
    pass_td: float = 4.0
    pass_int: float = -1.0
    pass_2pt: float = 2.0
    rush_yd: float = 0.1
    rush_td: float = 6.0
    rush_2pt: float = 2.0
    rec: float = 0.5
    rec_yd: float = 0.1
    rec_td: float = 6.0
    rec_2pt: float = 2.0
    fum_lost: float = -2.0
    st_td: float = 6.0  # special teams TD scored by an individual player

    # --- Kicker ---
    fg_0_19: float = 3.0
    fg_20_29: float = 3.0
    fg_30_39: float = 3.0
    fg_40_49: float = 4.0
    fg_50_plus: float = 5.0
    fg_miss: float = -1.0
    xp_made: float = 1.0
    xp_miss: float = -1.0

    # --- Team defense / special teams (DEF) ---
    def_sack: float = 1.0
    def_int: float = 2.0
    def_fum_rec: float = 2.0
    def_td: float = 6.0
    def_safety: float = 2.0
    def_block_kick: float = 2.0
    # Points-allowed tiers: (inclusive_upper_bound, points). Evaluated in order.
    pts_allowed_tiers: List[Tuple[int, float]] = field(
        default_factory=lambda: [
            (0, 10.0),
            (6, 7.0),
            (13, 4.0),
            (20, 1.0),
            (27, 0.0),
            (34, -1.0),
        ]
    )
    pts_allowed_35_plus: float = -4.0

    @classmethod
    def sleeper_default(cls) -> "ScoringRules":
        """Sleeper's default league scoring (half-PPR, 4-pt pass TD)."""
        return cls()

    # ------------------------------------------------------------------ #
    # Per-game scoring
    # ------------------------------------------------------------------ #

    def compute_offense_score(self, game: Dict) -> float:
        """Fantasy points for one game by a QB/RB/WR/TE."""
        score = (
            _num(game, "passing_yards") * self.pass_yd
            + _num(game, "passing_tds") * self.pass_td
            + _num(game, "passing_interceptions") * self.pass_int
            + _num(game, "passing_2pt_conversions") * self.pass_2pt
            + _num(game, "rushing_yards") * self.rush_yd
            + _num(game, "rushing_tds") * self.rush_td
            + _num(game, "rushing_2pt_conversions") * self.rush_2pt
            + _num(game, "receptions") * self.rec
            + _num(game, "receiving_yards") * self.rec_yd
            + _num(game, "receiving_tds") * self.rec_td
            + _num(game, "receiving_2pt_conversions") * self.rec_2pt
            + _num(game, "fumbles_lost_total") * self.fum_lost
            + _num(game, "special_teams_tds") * self.st_td
        )
        return round(score, 4)

    def compute_kicker_score(self, game: Dict) -> float:
        """Fantasy points for one game by a kicker."""
        made = (
            _num(game, "fg_made_0_19") * self.fg_0_19
            + _num(game, "fg_made_20_29") * self.fg_20_29
            + _num(game, "fg_made_30_39") * self.fg_30_39
            + _num(game, "fg_made_40_49") * self.fg_40_49
            + (_num(game, "fg_made_50_59") + _num(game, "fg_made_60_")) * self.fg_50_plus
        )
        missed = (_num(game, "fg_missed") + _num(game, "fg_blocked")) * self.fg_miss
        xp = (
            _num(game, "pat_made") * self.xp_made
            + (_num(game, "pat_missed") + _num(game, "pat_blocked")) * self.xp_miss
        )
        return round(made + missed + xp, 4)

    def points_allowed_score(self, points_allowed: float) -> float:
        for upper, pts in self.pts_allowed_tiers:
            if points_allowed <= upper:
                return pts
        return self.pts_allowed_35_plus

    def compute_dst_score(self, game: Dict) -> float:
        """Fantasy points for one game by a team defense/special teams unit.

        Expects a team-week row (nflverse stats_team) augmented with a
        'points_allowed' key (see data.build_dst_game_logs).
        """
        blocks = (
            _num(game, "def_punt_blocks")
            + _num(game, "def_pat_blocks")
            + _num(game, "def_fg_blocks")
        )
        tds = _num(game, "def_tds") + _num(game, "fumble_recovery_tds") + _num(
            game, "special_teams_tds"
        )
        score = (
            _num(game, "def_sacks") * self.def_sack
            + _num(game, "def_interceptions") * self.def_int
            + _num(game, "fumble_recovery_opp") * self.def_fum_rec
            + tds * self.def_td
            + _num(game, "def_safeties") * self.def_safety
            + blocks * self.def_block_kick
            + self.points_allowed_score(_num(game, "points_allowed"))
        )
        return round(score, 4)

    def compute_game_score(self, game: Dict, position: str) -> float:
        """Dispatch to the right scorer for a normalized fantasy position."""
        if position == "K":
            return self.compute_kicker_score(game)
        if position == "DEF":
            return self.compute_dst_score(game)
        return self.compute_offense_score(game)

    def compute_season_scores(self, game_log: List[Dict], position: str) -> List[float]:
        """Per-game fantasy points for a full season game log."""
        return [self.compute_game_score(g, position) for g in game_log]
