# nfl-statistics

Statistical framework for fantasy football draft preparation — a Value Over
Replacement (VOR) engine that turns real NFL game logs into a recommended
draft order. Sibling project to
[nba-statistics](https://github.com/LordSunchips/nba-statistics).

## How it works

1. **Data** — weekly player stats, team defense stats, and schedules are
   downloaded from [nflverse](https://github.com/nflverse/nflverse-data)
   and cached under `src/fantasy_football/assets/<season>/`. Offensive
   players are scored from their individual game logs; each team's defense
   is treated as a single `DEF` "player" built from team-level stats plus
   points allowed from the schedule.
2. **Scoring** — every game is scored with the league's rules. The default
   is Sleeper's default configuration: half-PPR, 4-pt passing TDs,
   -2 fumbles lost, distance-tiered kicker scoring with -1 misses, and
   tiered DEF points-allowed scoring.
3. **Base value** — `avg_score * availability - risk_aversion * std_dev`.
   Availability (games played / 17) penalizes injury-prone players;
   the standard-deviation term penalizes boom/bust inconsistency.
4. **Replacement level** — for each position, the base value of the first
   player projected to go undrafted as a starter:
   rank `num_teams * starting_spots`, with the league's FLEX slots
   allocated greedily to the best remaining RB/WR/TE before the
   replacement rank is fixed.
5. **VOR** — `base_value - replacement_value` at the player's position.
   Players are ranked by VOR descending: the recommended draft order.

## League settings

Defaults model a 12-team Sleeper league with starters
1 QB, 2 RB, 2 WR, 1 TE, 2 FLEX (W/R/T), 1 K, 1 DEF
(bench and IR slots don't affect replacement level).

## Usage

```bash
python3 main.py                    # 2025 season logs, 12 teams
python3 main.py --season 2024 --num-teams 10 --min-games 4
```

No third-party dependencies — Python 3.10+ standard library only.

Output: `reports/draft_order_<season>.csv` with columns
`overall_rank, position_rank, player, position, team, games_played,
avg_fantasy_pts, base_value, replacement_value, vor`.

## Caveats

- Base values are computed from last season's game logs, not forward
  projections — rookies are absent and situation changes (trades, new
  starters) aren't modeled.
- Pure VOR ranks elite K/DEF units higher (top ~50) than market drafts do;
  most leagues stream those positions, so feel free to discount them.

## Tests

```bash
python3 -m unittest discover -s tests
```
