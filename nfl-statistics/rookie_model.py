"""Supervised rookie projection: college production -> NFL rookie fantasy PPG.

Pipeline:
    1. Aggregate cfbfastR college play data into per-player seasons.
    2. Link nflverse draft picks (QB/RB/WR/TE) to college careers by name.
    3. Target: each rookie's actual NFL fantasy points per game in their
       draft season (Sleeper default scoring); 0 for players who never played.
    4. Model: ridge regression (alpha by 5-fold CV) on draft capital,
       position, and per-game college production features.

CLI: train on classes 2020-2024, validate on 2025, predict 2026.
The train_and_predict() entry point is reused by backtest.py and main.py
with other class windows.
"""
import argparse
import csv
import sys
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fantasy_football.college import (
    COLLEGE_CACHE, DRAFT_PICKS_URL, FEATURE_NAMES,
    build_college_cache, build_features, load_college_seasons,
    load_draft_picks, match_college, normalize_name,
)
from fantasy_football.data import ASSETS_DIR, download_assets, load_player_game_logs
from fantasy_football.ml import RidgeRegression, kfold_alpha_search, r_squared, spearman
from fantasy_football.scoring import ScoringRules

COLLEGE_SEASONS = list(range(2014, 2026))
ALPHAS = [0.1, 1.0, 3.0, 10.0, 30.0, 100.0]


def ensure_resources(cfb_raw_dir: Optional[Path] = None, rebuild: bool = False):
    """College cache + draft picks, downloaded/aggregated on first use."""
    if rebuild or not COLLEGE_CACHE.exists():
        build_college_cache(COLLEGE_SEASONS, cfb_raw_dir)
    draft_path = ASSETS_DIR / "draft_picks.csv"
    if not draft_path.exists():
        urllib.request.urlretrieve(DRAFT_PICKS_URL, draft_path)
    return load_college_seasons(), draft_path


def rookie_ppg(draft_year: int, rules: ScoringRules) -> Dict[str, float]:
    """{normalized_name: fantasy PPG in the player's draft season}."""
    logs, positions, _ = load_player_game_logs(draft_year)
    out = {}
    for name, log in logs.items():
        scores = rules.compute_season_scores(log, positions.get(name, ""))
        if scores:
            out[normalize_name(name)] = sum(scores) / len(scores)
    return out


def build_dataset(classes, picks, by_name, rules, with_target=True):
    X, y, meta = [], [], []
    targets = {c: rookie_ppg(c, rules) for c in classes} if with_target else {}
    for p in picks:
        if p["draft_year"] not in classes:
            continue
        college = match_college(p, by_name)
        if college is None:
            continue
        feats = build_features(p, college, rules)
        if feats is None:
            continue
        X.append(feats)
        meta.append(p)
        if with_target:
            y.append(targets[p["draft_year"]].get(normalize_name(p["name"]), 0.0))
    return X, y, meta


def train_and_predict(
    train_classes: List[int],
    predict_class: int,
    rules: ScoringRules,
    by_name: Dict,
    draft_path: Path,
) -> Tuple[List[Dict], RidgeRegression, float]:
    """Fit on train_classes, predict predict_class.

    Returns (predictions, model, cv_r2) where predictions is a list of
    {"player", "position", "team", "ppg", "round", "pick", "college"}
    sorted by predicted PPG descending.
    """
    picks = load_draft_picks(draft_path, train_classes + [predict_class])
    for season in train_classes:
        download_assets(season)
    Xtr, ytr, _ = build_dataset(train_classes, picks, by_name, rules)
    alpha, cv = kfold_alpha_search(Xtr, ytr, ALPHAS)
    model = RidgeRegression(alpha).fit(Xtr, ytr)

    Xp, _, mp = build_dataset([predict_class], picks, by_name, rules, with_target=False)
    preds = model.predict(Xp)
    out = [
        {"player": p["name"], "position": p["position"], "team": p["team"],
         "ppg": pred, "round": p["round"], "pick": p["pick"], "college": p["college"]}
        for p, pred in zip(mp, preds)
    ]
    out.sort(key=lambda r: -r["ppg"])
    return out, model, cv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfb-raw-dir", type=Path, default=None)
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--train-classes", type=int, nargs="+",
                        default=[2020, 2021, 2022, 2023, 2024])
    parser.add_argument("--val-class", type=int, default=2025)
    parser.add_argument("--predict-class", type=int, default=2026)
    args = parser.parse_args()

    rules = ScoringRules.sleeper_default()
    by_name, draft_path = ensure_resources(args.cfb_raw_dir, args.rebuild_cache)

    # Validation
    val_preds, model, cv = train_and_predict(
        args.train_classes, args.val_class, rules, by_name, draft_path
    )
    download_assets(args.val_class)
    actual = rookie_ppg(args.val_class, rules)
    yv = [actual.get(normalize_name(r["player"]), 0.0) for r in val_preds]
    pv = [r["ppg"] for r in val_preds]
    print(f"=== Validation on class of {args.val_class} "
          f"(trained {args.train_classes[0]}-{args.train_classes[-1]}, CV R^2 {cv:.3f}) ===")
    print(f"R^2:      {r_squared(yv, pv):.3f}")
    print(f"Spearman: {spearman(pv, yv):.3f}")
    for r, act in list(zip(val_preds, yv))[:12]:
        print(f"{r['player']:<26} pred {r['ppg']:>5.2f}  actual {act:>5.2f}")

    print("\nTop feature weights (standardized):")
    for name, w in sorted(zip(FEATURE_NAMES, model.weights), key=lambda t: -abs(t[1]))[:8]:
        print(f"  {name:<22} {w:>7.3f}")

    # Prediction for the upcoming class
    preds, _, _ = train_and_predict(
        args.train_classes + [args.val_class], args.predict_class, rules, by_name, draft_path
    )
    out = Path(__file__).parent / "reports" / f"rookie_predictions_{args.predict_class}.csv"
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "player", "position", "team", "college", "round", "pick",
                    "predicted_rookie_ppg"])
        for rank, r in enumerate(preds, 1):
            w.writerow([rank, r["player"], r["position"], r["team"], r["college"],
                        r["round"], r["pick"], round(r["ppg"], 2)])
    print(f"\n=== Predicted top-15 rookies, class of {args.predict_class} ===")
    for r in preds[:15]:
        print(f"{r['player']:<26} {r['position']:<3} {r['team']:<4} R{r['round']} "
              f"P{r['pick']:<4} -> {r['ppg']:.2f} PPG")
    print(f"\nWrote {len(preds)} rookie predictions to {out}")


if __name__ == "__main__":
    main()
