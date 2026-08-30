"""Backtest the VOR draft order.

Builds the draft board exactly as main.py would have before the 2025 season
(recency-weighted base values from 2020-2024), then grades it against actual
2025 fantasy production under the same scoring rules.

Metrics:
    - Spearman rank correlation, predicted order vs actual 2025 total points
    - Top-N hit rate (overlap of predicted vs actual top-N)
    - Value captured: actual points of predicted top-N vs hindsight-best top-N
    - The same metrics for a naive baseline (2024 season only) to show what
      the five-year weighting buys.

Usage::

    python3 backtest.py [--recency-decay 0.7]
"""
import argparse
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fantasy_football.analysis import generate_draft_order, write_draft_order_csv
from fantasy_football.data import download_assets, load_seasons
from fantasy_football.projection import VeteranProjector, build_summaries
from fantasy_football.scoring import ScoringRules
from fantasy_football.vor import LeagueSettings, VORCalculator


def spearman(xs: List[float], ys: List[float]) -> float:
    """Spearman rank correlation (average ranks for ties)."""
    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def actual_total_points(logs, positions, rules) -> Dict[str, float]:
    """Actual total fantasy points per player for the test season."""
    return {
        name: round(sum(rules.compute_season_scores(log, positions.get(name, ""))), 2)
        for name, log in logs.items()
    }


def actual_vor_values(actual: Dict[str, float], positions: Dict[str, str],
                      settings: LeagueSettings) -> Dict[str, float]:
    """Hindsight VOR: actual total points minus the actual replacement level
    at each position (flex-aware, same machinery as the draft board)."""
    calc = VORCalculator(settings)
    repl = calc.compute_replacement_values(actual, positions)
    return {p: actual[p] - repl.get(positions.get(p, ""), 0.0) for p in actual}


def evaluate(predicted_order: List[str], actual: Dict[str, float],
             actual_vor: Dict[str, float], label: str) -> Dict:
    """Grade a predicted draft order against actual production.

    Two value-captured denominations:
      raw — share of total points vs the hindsight-best top-N. Biased
            toward QBs (raw leaderboards are QB-heavy), reported for
            continuity.
      vor — share of points ABOVE POSITIONAL REPLACEMENT vs the
            hindsight-best top-N by that measure. This is the metric a
            draft is actually trying to maximize.
    """
    common = [p for p in predicted_order if p in actual]
    pred_rank_vals = [-i for i, _ in enumerate(common)]  # earlier pick = higher value
    actual_vals = [actual[p] for p in common]
    rho_all = spearman(pred_rank_vals, actual_vals)
    top150 = common[:150]
    rho150 = spearman([-i for i in range(len(top150))], [actual[p] for p in top150])

    hindsight = sorted(actual, key=lambda p: -actual[p])
    hindsight_vor = sorted(actual_vor, key=lambda p: -actual_vor[p])
    results = {"label": label, "spearman_all": rho_all, "spearman_top150": rho150,
               "coverage": len(common), "hits": {}, "value_captured": {},
               "vor_captured": {}}
    for n in (12, 24, 50, 100):
        pred_top = set(common[:n])
        act_top = set(hindsight[:n])
        results["hits"][n] = len(pred_top & act_top)
        pred_pts = sum(actual[p] for p in common[:n])
        best_pts = sum(actual[p] for p in hindsight[:n])
        results["value_captured"][n] = pred_pts / best_pts if best_pts else 0.0
        pred_vor = sum(actual_vor[p] for p in common[:n])
        best_vor = sum(actual_vor[p] for p in hindsight_vor[:n])
        results["vor_captured"][n] = pred_vor / best_vor if best_vor else 0.0
    return results


def report(res: Dict) -> None:
    print(f"\n=== {res['label']} ===")
    print(f"Players graded: {res['coverage']}")
    print(f"Spearman rank correlation (all graded):    {res['spearman_all']:.3f}")
    print(f"Spearman rank correlation (predicted top 150): {res['spearman_top150']:.3f}")
    print(f"{'Top-N':>6} {'hits':>6} {'raw value':>10} {'VOR value':>10}")
    for n in (12, 24, 50, 100):
        print(f"{n:>6} {res['hits'][n]:>4}/{n:<3} {res['value_captured'][n]:>9.1%} "
              f"{res['vor_captured'][n]:>9.1%}")


def rookie_projections_for(test_season: int, rules: ScoringRules, top_n: int):
    """Leakage-free rookie projections for the test season's draft class:
    the model is trained only on classes before the test season."""
    from rookie_model import ensure_resources, train_and_predict

    by_name, draft_path = ensure_resources()
    train_classes = list(range(test_season - 5, test_season))
    preds, _, _ = train_and_predict(train_classes, test_season, rules, by_name, draft_path)
    return preds[:top_n]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test-season", type=int, default=2025)
    parser.add_argument("--recency-decay", type=float, default=0.5)
    parser.add_argument("--num-teams", type=int, default=12)
    parser.add_argument("--blend", type=float, default=1.0,
                        help="weight on the supervised model vs weighted history (1.0 = model only)")
    parser.add_argument("--embed-rookies", type=int, default=12,
                        help="embed top-N projected rookies into the board (0 = off)")
    args = parser.parse_args()
    test_season = args.test_season
    train_seasons = list(range(test_season - 5, test_season))

    for season in train_seasons + [test_season]:
        download_assets(season)

    train_logs, train_pos, train_teams = load_seasons(train_seasons)
    test_logs_by_season, test_pos, _ = load_seasons([test_season])
    test_logs = test_logs_by_season[test_season]

    settings = LeagueSettings(num_teams=args.num_teams, recency_decay=args.recency_decay)
    rules = settings.scoring_rules
    actual = actual_total_points(test_logs, test_pos, rules)

    actual_vor = actual_vor_values(actual, test_pos, settings)

    rookies = rookie_projections_for(test_season, rules, args.embed_rookies) \
        if args.embed_rookies else []
    if rookies:
        print(f"Embedded rookies ({len(rookies)}): "
              + ", ".join(r["player"] for r in rookies))

    # --- Strategy under test: supervised veteran projection model ---
    model_seasons = list(range(2014, test_season))
    for season in model_seasons:
        download_assets(season)
    model_logs, model_pos, _ = load_seasons(model_seasons)
    summaries = build_summaries(model_logs, model_pos, rules)
    proj = VeteranProjector().fit(
        summaries, model_pos, list(range(2017, test_season))
    )
    print(f"VeteranProjector: alpha {proj.alpha}, CV R^2 {proj.cv_r2:.3f} "
          f"(targets 2017-{test_season - 1})")
    predictions = proj.predict_season(summaries, model_pos, test_season)
    if args.blend < 1.0:
        from fantasy_football.vor import compute_weighted_base_value
        for name in predictions:
            season_logs = {s: train_logs[s][name] for s in train_logs if name in train_logs[s]}
            wb = compute_weighted_base_value(
                season_logs, rules, train_pos.get(name, ""),
                settings.season_games, settings.risk_aversion, settings.recency_decay,
            )
            predictions[name] = round(args.blend * predictions[name] + (1 - args.blend) * wb, 4)
    model_rows = generate_draft_order(
        train_logs, dict(train_pos), settings, dict(train_teams),
        rookie_projections=rookies, base_value_override=predictions,
    )
    model_res = evaluate([r["player"] for r in model_rows], actual, actual_vor,
                         f"Supervised model (blend {args.blend}) + top-{len(rookies)} rookies")

    # --- Previous engine: weighted VOR board with rookies embedded ---
    rows = generate_draft_order(train_logs, dict(train_pos), settings, dict(train_teams),
                                rookie_projections=rookies)
    predicted = [r["player"] for r in rows]
    label = (f"{len(train_seasons)}-season weighted VOR (decay {args.recency_decay})"
             + (f" + top-{len(rookies)} rookies" if rookies else ""))
    main_res = evaluate(predicted, actual, actual_vor, label)

    # --- Baseline: last season only ---
    last = train_seasons[-1]
    baseline_rows = generate_draft_order(
        {last: train_logs[last]}, dict(train_pos), settings, dict(train_teams)
    )
    base_res = evaluate([r["player"] for r in baseline_rows], actual, actual_vor,
                        f"Baseline: {last} season only")

    # --- Oracle ceiling: perfect foresight over the same candidate pool ---
    pool = {r["player"] for r in model_rows}
    oracle_order = sorted((p for p in actual if p in pool), key=lambda p: -actual[p])
    oracle_res = evaluate(oracle_order, actual, actual_vor,
                          "Oracle ceiling (perfect ranking of the same pool)")

    report(model_res)
    report(main_res)
    report(base_res)
    report(oracle_res)

    rows = model_rows  # detail CSV shows the best board

    # How much 2025 production was undraftable (rookies etc.)?
    hindsight = sorted(actual, key=lambda p: -actual[p])
    known = set(predicted)
    missing = [p for p in hindsight[:100] if p not in known]
    print(f"\nTop-100 finishers missing from the graded board: {len(missing)}")
    print("  " + ", ".join(missing[:12]) + (" …" if len(missing) > 12 else ""))

    # Per-player detail CSV
    out = Path(__file__).parent / "reports" / f"backtest_{test_season}.csv"
    detail = []
    hindsight_rank = {p: i + 1 for i, p in enumerate(hindsight)}
    for r in rows:
        name = r["player"]
        detail.append({
            "predicted_rank": r["overall_rank"],
            "player": name,
            "position": r["position"],
            "predicted_vor": r["vor"],
            "actual_2025_points": actual.get(name, ""),
            "actual_2025_rank": hindsight_rank.get(name, ""),
        })
    import csv
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(detail[0].keys()))
        w.writeheader()
        w.writerows(detail)
    print(f"\nWrote per-player detail to {out}")


if __name__ == "__main__":
    main()
