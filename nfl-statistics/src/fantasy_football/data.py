"""Load nflverse weekly stats into per-player game logs.

Assets (downloaded by main.py, cached under assets/<season>/):
    stats_player_week_<season>.csv.gz — one row per player-game
    stats_team_week_<season>.csv.gz   — one row per team-game
    games.csv                         — schedule with final scores

Game logs are lists of dict rows (raw nflverse columns). DEF logs are
team-week rows augmented with 'points_allowed' from the schedule.
"""
from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import Dict, List, Tuple

ASSETS_DIR = Path(__file__).parent / "assets"

# Fantasy-relevant positions; FB counts as RB.
_POSITION_MAP: Dict[str, str] = {
    "QB": "QB",
    "RB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "K": "K",
}

NFLVERSE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"

ASSET_URLS = {
    "stats_player_week_{season}.csv.gz": NFLVERSE_BASE + "/stats_player/stats_player_week_{season}.csv.gz",
    "stats_team_week_{season}.csv.gz": NFLVERSE_BASE + "/stats_team/stats_team_week_{season}.csv.gz",
    "games.csv": NFLVERSE_BASE + "/schedules/games.csv",
}


def download_assets(season: int) -> Path:
    """Download the season's asset files if not already cached."""
    import urllib.request

    season_dir = ASSETS_DIR / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)
    for name_tpl, url_tpl in ASSET_URLS.items():
        name = name_tpl.format(season=season)
        dest = season_dir / name
        if dest.exists():
            continue
        url = url_tpl.format(season=season)
        print(f"Downloading {url} -> {dest}")
        urllib.request.urlretrieve(url, dest)
    return season_dir


def _read_csv(path: Path) -> List[Dict]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as fh:
        return list(csv.DictReader(fh))


def load_player_game_logs(
    season: int,
) -> Tuple[Dict[str, List[Dict]], Dict[str, str], Dict[str, str]]:
    """Build per-player regular-season game logs.

    Returns (game_logs, positions, teams):
        game_logs — {player_display_name: [game rows]}
        positions — {player_display_name: normalized position}
        teams     — {player_display_name: most recent team}
    """
    rows = _read_csv(ASSETS_DIR / str(season) / f"stats_player_week_{season}.csv.gz")
    game_logs: Dict[str, List[Dict]] = {}
    positions: Dict[str, str] = {}
    teams: Dict[str, str] = {}
    for row in rows:
        if row.get("season_type") != "REG":
            continue
        pos = _POSITION_MAP.get(row.get("position", ""))
        if pos is None:
            continue
        name = row["player_display_name"]
        game_logs.setdefault(name, []).append(row)
        positions[name] = pos
        teams[name] = row.get("team", "")
    return game_logs, positions, teams


def _points_allowed_by_team_week(season: int) -> Dict[Tuple[str, int], float]:
    """Map (team, week) -> points allowed, from the schedule's final scores."""
    games = _read_csv(ASSETS_DIR / str(season) / "games.csv")
    allowed: Dict[Tuple[str, int], float] = {}
    for g in games:
        if int(g["season"]) != season or g.get("game_type") != "REG":
            continue
        if g.get("home_score") in ("", "NA", None):
            continue
        week = int(g["week"])
        allowed[(g["home_team"], week)] = float(g["away_score"])
        allowed[(g["away_team"], week)] = float(g["home_score"])
    return allowed


def build_dst_game_logs(season: int) -> Tuple[Dict[str, List[Dict]], Dict[str, str], Dict[str, str]]:
    """Build per-team DEF game logs from team-week stats plus points allowed.

    DEF units are named '<TEAM> D/ST' and treated as players at position DEF.
    """
    rows = _read_csv(ASSETS_DIR / str(season) / f"stats_team_week_{season}.csv.gz")
    allowed = _points_allowed_by_team_week(season)
    game_logs: Dict[str, List[Dict]] = {}
    positions: Dict[str, str] = {}
    teams: Dict[str, str] = {}
    for row in rows:
        if row.get("season_type") != "REG":
            continue
        team = row["team"]
        key = (team, int(row["week"]))
        if key not in allowed:
            continue
        row = dict(row)
        row["points_allowed"] = allowed[key]
        name = f"{team} D/ST"
        game_logs.setdefault(name, []).append(row)
        positions[name] = "DEF"
        teams[name] = team
    return game_logs, positions, teams


def load_all_game_logs(season: int):
    """Player + DEF game logs, positions, and teams for one season."""
    logs, pos, teams = load_player_game_logs(season)
    dst_logs, dst_pos, dst_teams = build_dst_game_logs(season)
    logs.update(dst_logs)
    pos.update(dst_pos)
    teams.update(dst_teams)
    return logs, pos, teams


def load_seasons(seasons: List[int]):
    """Load game logs for multiple seasons.

    Returns (logs_by_season, positions, teams):
        logs_by_season — {season: {player: [game rows]}}
        positions/teams — merged across seasons, most recent season wins.
    """
    logs_by_season: Dict[int, Dict[str, List[Dict]]] = {}
    positions: Dict[str, str] = {}
    teams: Dict[str, str] = {}
    for season in sorted(seasons):
        logs, pos, tm = load_all_game_logs(season)
        logs_by_season[season] = logs
        positions.update(pos)  # later (more recent) seasons overwrite
        teams.update(tm)
    return logs_by_season, positions, teams
