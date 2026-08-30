"""High-level analysis: generate a VOR-ordered draft board."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from fantasy_football.vor import LeagueSettings, VORCalculator, compute_base_value

REPORT_COLUMNS = [
    "overall_rank",
    "position_rank",
    "player",
    "position",
    "team",
    "games_played",
    "avg_fantasy_pts",
    "base_value",
    "replacement_value",
    "vor",
]


def generate_draft_order(
    game_logs: Dict[str, List[Dict]],
    player_positions: Dict[str, str],
    league_settings: LeagueSettings,
    player_teams: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    """Rank all players by VOR — the recommended draft order.

    Returns a list of row dicts (see REPORT_COLUMNS) sorted by VOR
    descending. Ties break on base_value, then name.
    """
    rules = league_settings.scoring_rules
    calc = VORCalculator(league_settings)
    player_teams = player_teams or {}

    base_values = {
        name: compute_base_value(
            log,
            rules,
            player_positions.get(name, ""),
            league_settings.season_games,
            league_settings.risk_aversion,
        )
        for name, log in game_logs.items()
    }
    replacement = calc.compute_replacement_values(base_values, player_positions)
    vor = calc.compute_vor(base_values, replacement, player_positions)

    rows = []
    for name, v in vor.items():
        pos = player_positions.get(name, "?")
        log = game_logs.get(name, [])
        scores = rules.compute_season_scores(log, pos)
        avg = round(sum(scores) / len(scores), 2) if scores else 0.0
        rows.append(
            {
                "player": name,
                "position": pos,
                "team": player_teams.get(name, ""),
                "games_played": len(log),
                "avg_fantasy_pts": avg,
                "base_value": base_values[name],
                "replacement_value": replacement.get(pos, 0.0),
                "vor": v,
            }
        )

    rows.sort(key=lambda r: (-r["vor"], -r["base_value"], r["player"]))
    pos_counts: Dict[str, int] = {}
    for i, row in enumerate(rows):
        row["overall_rank"] = i + 1
        pos_counts[row["position"]] = pos_counts.get(row["position"], 0) + 1
        row["position_rank"] = pos_counts[row["position"]]
    return rows


def write_draft_order_csv(rows: List[Dict], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in REPORT_COLUMNS})
    return path
