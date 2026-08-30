"""Build the VOR draft board.

Downloads nflverse weekly stats for the source seasons (cached under
src/fantasy_football/assets/), scores every player and D/ST unit with the
league's rules, computes recency-weighted multi-season base values, and
writes reports/draft_order_<latest-season>.csv ranked by VOR.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fantasy_football.data import download_assets, load_seasons
from fantasy_football.analysis import generate_draft_order, write_draft_order_csv
from fantasy_football.vor import LeagueSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025, help="most recent source season")
    parser.add_argument("--num-seasons", type=int, default=5, help="seasons of history to weight")
    parser.add_argument("--recency-decay", type=float, default=0.7,
                        help="per-year weight decay for older seasons (1.0 = flat average)")
    parser.add_argument("--num-teams", type=int, default=12)
    parser.add_argument("--risk-aversion", type=float, default=0.1)
    parser.add_argument("--min-games", type=int, default=1,
                        help="exclude players with fewer games in the latest season")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    seasons = list(range(args.season - args.num_seasons + 1, args.season + 1))
    for season in seasons:
        download_assets(season)
    logs_by_season, positions, teams = load_seasons(seasons)
    logs_by_season[args.season] = {
        n: log for n, log in logs_by_season[args.season].items() if len(log) >= args.min_games
    }

    settings = LeagueSettings(
        num_teams=args.num_teams,
        risk_aversion=args.risk_aversion,
        recency_decay=args.recency_decay,
    )
    rows = generate_draft_order(logs_by_season, positions, settings, teams)

    output = args.output or Path(__file__).parent / "reports" / f"draft_order_{args.season}.csv"
    write_draft_order_csv(rows, output)
    print(f"Wrote {len(rows)} players to {output} (seasons {seasons[0]}-{seasons[-1]}, decay {args.recency_decay})")
    for row in rows[:15]:
        print(
            f"{row['overall_rank']:>3}. {row['player']:<24} {row['position']:<4}"
            f"{row['team']:<4} VOR={row['vor']:>7.2f}  base={row['base_value']:>6.2f}"
            f"  seasons={row['seasons_used']}"
        )


if __name__ == "__main__":
    main()
