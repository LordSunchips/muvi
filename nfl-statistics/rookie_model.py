"""Supervised rookie projection: college production -> NFL rookie fantasy PPG.

Pipeline:
    1. Aggregate cfbfastR college play data into per-player seasons.
    2. Link nflverse draft picks (QB/RB/WR/TE) to college careers by name.
    3. Target: each rookie's actual NFL fantasy points per game in their
       draft season (Sleeper default scoring); 0 for players who never played.
    4. Model: ridge regression (alpha by 5-fold CV) on draft capital,
       position, and per-game college production features.
    5. Train on classes 2020-2024, validate on the class of 2025, predict
       the class of 2026.

Output: reports/rookie_predictions_2026.csv
"""
import argparse
import csv
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fantasy_football.college import (
    COLLEGE_CACHE, DRAFT_PICKS_URL, FEATURE_NAMES,
    build_college_cache, build_features, load_college_seasons,
    load_draft_picks, match_college, normalize_name,
)
from fantasy_football.data import ASSETS_DIR, download_assets, load_player_game_logs
from fantasy_football.ml import RidgeRegression, kfold_alpha_search, r_squared, spearman
from fantasy_football.scoring import ScoringRules

TRAIN_CLASSES = [2020, 2021, 2022, 2023, 2024]
VAL_CLASS = 2025
PREDICT_CLASS = 2026
COLLEGE_SEASONS = list(range(2014, 2026))


def rookie_ppg(draft_year: int, rules: ScoringRules) -> dict:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cfb-raw-dir", type=Path, default=None,
                        help="directory with player_stats_<season>.csv files (else downloaded)")
    parser.add_argument("--rebuild-cache", action="store_true")
    args = parser.parse_args()

    rules = ScoringRules.sleeper_default()

    if args.rebuild_cache or not COLLEGE_CACHE.exists():
        build_college_cache(COLLEGE_SEASONS, args.cfb_raw_dir)
    by_name = load_college_seasons()

    draft_path = ASSETS_DIR / "draft_picks.csv"
    if not draft_path.exists():
        urllib.request.urlretrieve(DRAFT_PICKS_URL, draft_path)
    picks = load_draft_picks(draft_path, TRAIN_CLASSES + [VAL_CLASS, PREDICT_CLASS])
    for season in TRAIN_CLASSES + [VAL_CLASS]:
        download_assets(season)

    Xtr, ytr, mtr = build_dataset(TRAIN_CLASSES, picks, by_name, rules)
    Xval, yval, mval = build_dataset([VAL_CLASS], picks, by_name, rules)
    print(f"Training rows (classes {TRAIN_CLASSES[0]}-{TRAIN_CLASSES[-1]}): {len(Xtr)}")
    print(f"Validation rows (class {VAL_CLASS}): {len(Xval)}")

    alpha, cv = kfold_alpha_search(Xtr, ytr, [0.1, 1.0, 3.0, 10.0, 30.0, 100.0])
    model = RidgeRegression(alpha).fit(Xtr, ytr)
    print(f"Chosen ridge alpha: {alpha} (CV R^2 {cv:.3f})")

    pval = model.predict(Xval)
    print(f"\n=== Validation on class of {VAL_CLASS} ===")
    print(f"R^2:      {r_squared(yval, pval):.3f}")
    print(f"Spearman: {spearman(pval, yval):.3f}")
    top = sorted(range(len(pval)), key=lambda i: -pval[i])[:12]
    print(f"{'Predicted top-12 rookie':<26} {'pred PPG':>8} {'actual PPG':>10}")
    for i in top:
        print(f"{mval[i]['name']:<26} {pval[i]:>8.2f} {yval[i]:>10.2f}")

    print(f"\nFeature weights (standardized):")
    for name, w in sorted(zip(FEATURE_NAMES, model.weights), key=lambda t: -abs(t[1]))[:8]:
        print(f"  {name:<22} {w:>7.3f}")

    Xp, _, mp = build_dataset([PREDICT_CLASS], picks, by_name, rules, with_target=False)
    preds = model.predict(Xp)
    order = sorted(range(len(preds)), key=lambda i: -preds[i])
    out = Path(__file__).parent / "reports" / f"rookie_predictions_{PREDICT_CLASS}.csv"
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "player", "position", "college", "round", "pick",
                    "predicted_rookie_ppg"])
        for rank, i in enumerate(order, 1):
            p = mp[i]
            w.writerow([rank, p["name"], p["position"], p["college"],
                        p["round"], p["pick"], round(preds[i], 2)])
    print(f"\n=== Predicted top-15 rookies, class of {PREDICT_CLASS} ===")
    for i in order[:15]:
        p = mp[i]
        print(f"{p['name']:<26} {p['position']:<3} {p['college']:<16} "
              f"R{p['round']} P{p['pick']:<3} -> {preds[i]:.2f} PPG")
    print(f"\nWrote {len(preds)} rookie predictions to {out}")


if __name__ == "__main__":
    main()
