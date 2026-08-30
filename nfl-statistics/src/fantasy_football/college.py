"""College-to-NFL rookie pipeline.

Aggregates cfbfastR play-attribution data into per-player college seasons,
links drafted players (nflverse draft_picks) to their college careers by
normalized name, and builds feature vectors for the rookie projection model.

Raw college data: one row per play with rusher / receiver / passer
attributions (sportsdataverse/cfbfastR-data, player_stats/csv/).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fantasy_football.scoring import ScoringRules

ASSETS_DIR = Path(__file__).parent / "assets"
COLLEGE_CACHE = ASSETS_DIR / "college" / "college_season_stats.csv"
DRAFT_PICKS_URL = "https://github.com/nflverse/nflverse-data/releases/download/draft_picks/draft_picks.csv"
CFB_RAW_URL = "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/master/player_stats/csv/player_stats_{season}.csv"

OFFENSE_POSITIONS = ("QB", "RB", "WR", "TE")

_SUFFIXES = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")


def normalize_name(name: str) -> str:
    n = re.sub(r"[^a-z ]", "", name.lower().replace(".", ""))
    n = _SUFFIXES.sub("", n)
    return " ".join(n.split())


COLLEGE_STAT_FIELDS = [
    "games", "rush_att", "rush_yds", "rush_td", "rec", "rec_yds", "rec_td",
    "cmp", "pass_att", "pass_yds", "pass_td", "int_thrown",
]


def aggregate_college_season(path: Path) -> Dict[Tuple[str, str], Dict]:
    """Aggregate one season's play-attribution file to per-player stats.

    Returns {(player_id, player_name): stats_dict}.
    """
    players: Dict[Tuple[str, str], Dict] = {}
    games: Dict[Tuple[str, str], set] = {}

    def bump(pid, name, game_id, **stats):
        if pid in ("", "NA", None) or name in ("", "NA", None):
            return
        key = (pid, name)
        row = players.setdefault(key, {f: 0.0 for f in COLLEGE_STAT_FIELDS})
        games.setdefault(key, set()).add(game_id)
        for k, v in stats.items():
            row[k] += v

    def num(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            gid = r["game_id"]
            td = r.get("touchdown_player_id") not in ("", "NA", None)
            if r.get("rush_player_id") not in ("", "NA", None):
                bump(r["rush_player_id"], r["rush_player"], gid,
                     rush_att=1, rush_yds=num(r["rush_yds"]),
                     rush_td=1 if td and r["touchdown_player_id"] == r["rush_player_id"] else 0)
            if r.get("reception_player_id") not in ("", "NA", None):
                bump(r["reception_player_id"], r["reception_player"], gid,
                     rec=1, rec_yds=num(r["reception_yds"]),
                     rec_td=1 if td and r["touchdown_player_id"] == r["reception_player_id"] else 0)
            if r.get("completion_player_id") not in ("", "NA", None):
                bump(r["completion_player_id"], r["completion_player"], gid,
                     cmp=1, pass_att=1, pass_yds=num(r["completion_yds"]),
                     pass_td=1 if td and r.get("reception_player_id") not in ("", "NA", None) else 0)
            if r.get("incompletion_player_id") not in ("", "NA", None):
                bump(r["incompletion_player_id"], r["incompletion_player"], gid, pass_att=1)
            if r.get("interception_thrown_player_id") not in ("", "NA", None):
                bump(r["interception_thrown_player_id"], r["interception_thrown_player"], gid,
                     int_thrown=1)

    for key, row in players.items():
        row["games"] = float(len(games[key]))
    return players


def build_college_cache(seasons: List[int], raw_dir: Optional[Path] = None,
                        cache_path: Path = COLLEGE_CACHE) -> Path:
    """Aggregate raw play files into a compact per-player-season CSV.

    raw_dir may hold player_stats_<season>.csv files; missing files are
    downloaded from cfbfastR-data.
    """
    import urllib.request

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", newline="") as out:
        w = csv.writer(out)
        w.writerow(["season", "player_id", "player"] + COLLEGE_STAT_FIELDS)
        for season in seasons:
            path = (raw_dir / f"player_stats_{season}.csv") if raw_dir else None
            if path is None or not path.exists():
                path = cache_path.parent / f"player_stats_{season}.csv"
                if not path.exists():
                    print(f"Downloading college play data {season}…")
                    urllib.request.urlretrieve(CFB_RAW_URL.format(season=season), path)
            for (pid, name), row in aggregate_college_season(path).items():
                w.writerow([season, pid, name] + [row[f] for f in COLLEGE_STAT_FIELDS])
    return cache_path


def load_college_seasons(cache_path: Path = COLLEGE_CACHE) -> Dict[str, List[Dict]]:
    """{normalized_name: [season rows]} from the aggregated cache."""
    by_name: Dict[str, List[Dict]] = {}
    with open(cache_path, newline="") as fh:
        for r in csv.DictReader(fh):
            row = {k: (float(v) if k in COLLEGE_STAT_FIELDS or k == "season" else v)
                   for k, v in r.items()}
            by_name.setdefault(normalize_name(r["player"]), []).append(row)
    return by_name


def load_draft_picks(path: Path, classes: List[int]) -> List[Dict]:
    """Offensive skill players from the given draft classes."""
    picks = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if not r["season"] or int(r["season"]) not in classes:
                continue
            if r["position"] not in OFFENSE_POSITIONS:
                continue
            picks.append({
                "draft_year": int(r["season"]),
                "round": int(r["round"]),
                "pick": int(r["pick"]),
                "name": r["pfr_player_name"],
                "position": r["position"],
                "college": r["college"],
            })
    return picks


FEATURE_NAMES = [
    "round", "pick", "is_rb", "is_wr", "is_te",
    "final_games", "final_rush_att_pg", "final_rush_yds_pg", "final_rush_td_pg",
    "final_rec_pg", "final_rec_yds_pg", "final_rec_td_pg",
    "final_pass_att_pg", "final_pass_yds_pg", "final_pass_td_pg", "final_int_pg",
    "final_fantasy_ppg", "career_seasons", "career_fantasy_ppg", "final_yds_per_carry",
]


def _fantasy_pts(row: Dict, rules: ScoringRules) -> float:
    return (
        row["pass_yds"] * rules.pass_yd + row["pass_td"] * rules.pass_td
        + row["int_thrown"] * rules.pass_int
        + row["rush_yds"] * rules.rush_yd + row["rush_td"] * rules.rush_td
        + row["rec"] * rules.rec + row["rec_yds"] * rules.rec_yd
        + row["rec_td"] * rules.rec_td
    )


def build_features(pick: Dict, college_rows: List[Dict], rules: ScoringRules) -> Optional[List[float]]:
    """Feature vector for one drafted player, or None if college data is unusable."""
    rows = [r for r in college_rows if r["season"] < pick["draft_year"]]
    if not rows:
        return None
    rows.sort(key=lambda r: r["season"])
    final = rows[-1]
    g = final["games"] or 1.0
    career_g = sum(r["games"] for r in rows) or 1.0
    career_pts = sum(_fantasy_pts(r, rules) for r in rows)
    return [
        float(pick["round"]),
        float(pick["pick"]),
        1.0 if pick["position"] == "RB" else 0.0,
        1.0 if pick["position"] == "WR" else 0.0,
        1.0 if pick["position"] == "TE" else 0.0,
        final["games"],
        final["rush_att"] / g, final["rush_yds"] / g, final["rush_td"] / g,
        final["rec"] / g, final["rec_yds"] / g, final["rec_td"] / g,
        final["pass_att"] / g, final["pass_yds"] / g, final["pass_td"] / g,
        final["int_thrown"] / g,
        _fantasy_pts(final, rules) / g,
        float(len(rows)),
        career_pts / career_g,
        final["rush_yds"] / final["rush_att"] if final["rush_att"] else 0.0,
    ]


def match_college(pick: Dict, by_name: Dict[str, List[Dict]]) -> Optional[List[Dict]]:
    """Find a drafted player's college rows by normalized name.

    Sanity-checks the stat profile against the draft position to avoid
    same-name collisions (a QB must have pass attempts, etc.).
    """
    rows = by_name.get(normalize_name(pick["name"]))
    if not rows:
        return None
    pre = [r for r in rows if r["season"] < pick["draft_year"]]
    if not pre:
        return None
    pos = pick["position"]
    total = {f: sum(r[f] for r in pre) for f in COLLEGE_STAT_FIELDS}
    if pos == "QB" and total["pass_att"] < 50:
        return None
    if pos == "RB" and total["rush_att"] < 30:
        return None
    if pos in ("WR", "TE") and total["rec"] < 10:
        return None
    return pre
