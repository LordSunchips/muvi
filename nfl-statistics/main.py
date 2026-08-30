"""Build the VOR draft board.

Downloads nflverse weekly stats for the source season (cached under
src/fantasy_football/assets/), scores every player and D/ST unit with the
league's rules, and writes reports/draft_order_<season>.csv ranked by VOR.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fantasy_football.data import download_assets, load_all_game_logs
from fantasy_football.analysis import generate_draft_order, write_draft_order_csv
from fantasy_football.vor import LeagueSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2025, help="source season for game logs")
    parser.add_argument("--num-teams", type=int, default=12)
    parser.add_argument("--risk-aversion", type=float, default=0.1)
    parser.add_argument("--min-games", type=int, default=1, help="exclude players with fewer games")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    download_assets(args.season)
    game_logs, positions, teams = load_all_game_logs(args.season)
    game_logs = {n: log for n, log in game_logs.items() if len(log) >= args.min_games}

    settings = LeagueSettings(num_teams=args.num_teams, risk_aversion=args.risk_aversion)
    rows = generate_draft_order(game_logs, positions, settings, teams)

    output = args.output or Path(__file__).parent / "reports" / f"draft_order_{args.season}.csv"
    write_draft_order_csv(rows, output)
    print(f"Wrote {len(rows)} players to {output}")
    for row in rows[:15]:
        print(
            f"{row['overall_rank']:>3}. {row['player']:<24} {row['position']:<4}"
            f"{row['team']:<4} VOR={row['vor']:>7.2f}  base={row['base_value']:>6.2f}"
        )


if __name__ == "__main__":
    main()
