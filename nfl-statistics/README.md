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
3. **Base value** — the default engine (`--engine model`) is a supervised
   projection: a ridge regression trained on 2014-present season-to-season
   transitions predicts each player's next-season fantasy points per
   roster slot (total/17) from three lagged seasons of production
   (fantasy PPG, recent form), opportunity (carries, targets, pass
   attempts per game), durability (games played), TD rate vs yardage
   (TDs regress, yardage persists), experience, and position. The model
   learns its own recency weights and aging effects from data.
   `--engine weighted` falls back to the closed-form alternative: per
   season, `avg_score * availability - risk_aversion * std_dev`, combined
   with recency weights `decay^seasons_ago` (default 0.5) renormalized
   over the seasons a player actually has. Either way, players absent
   from the most recent season are excluded.
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
python3 main.py                    # 2021-2025 logs, decay 0.7, 12 teams
python3 main.py --num-seasons 3 --recency-decay 0.5 --num-teams 10 --min-games 4
```

No third-party dependencies — Python 3.10+ standard library only.

Output: `reports/draft_order_<season>.csv` with columns
`overall_rank, position_rank, player, position, team, seasons_used,
games_latest_season, avg_pts_latest_season, base_value,
replacement_value, vor`.

## Caveats

- Base values are computed from historical game logs, not forward
  projections — incoming rookies are absent and situation changes
  (trades, new starters) aren't modeled.
- Pure VOR ranks elite K/DEF units higher (top ~50) than market drafts do;
  most leagues stream those positions, so feel free to discount them.

## Tests

```bash
python3 -m unittest discover -s tests
```

## Backtest

`python3 backtest.py --test-season <year>` trains every component only
on data available before the test season (no leakage) and grades the
board against actual production: Spearman rank correlation, top-N hit
rates, and value captured vs a perfect-hindsight board — in two
denominations. *Raw* value captured compares total points against the
hindsight-best top-N, which is QB-dominated and therefore flatters
QB-heavy boards; *VOR* value captured compares points above positional
replacement, the quantity a draft actually maximizes. An oracle row
(perfect ranking of the same candidate pool) bounds what any model
could score: because breakout late-round rookies are invisible and
hindsight-best top-N is dominated by unpredictable outlier seasons, the
oracle itself captures only ~60-88% of VOR value — treat these
percentages as relative comparisons, not absolute grades. Results for
2023-2025: `reports/backtest_<year>.csv` and
`reports/backtest_summary.txt`.

## Rookie projections (supervised ML)

`python3 rookie_model.py` aggregates college play-attribution data
(sportsdataverse/cfbfastR-data, 2014-2025) into per-player college
seasons, links nflverse draft picks to their college careers, and trains
a ridge regression (stdlib implementation, alpha via 5-fold CV) to
predict rookie-season fantasy PPG from draft capital, position, and
per-game college production. Trained on classes 2020-2024, validated on
the class of 2025 (R^2 ≈ 0.34, Spearman ≈ 0.49), and used to project the
class of 2026: `reports/rookie_predictions_2026.csv`. The top 12
projected rookies are embedded into the main draft board
(`main.py --embed-rookies N`, 0 to disable): each enters the player pool
with base_value = predicted rookie PPG and competes for draft slots and
replacement levels like a veteran.
