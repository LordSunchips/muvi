"""Minimal supervised-learning toolkit (standard library only).

Ridge regression with feature standardization, solved in closed form
(X'X + lambda*I) w = X'y via Gaussian elimination. Small feature counts and
a few hundred rows — no numerical libraries required.
"""
from __future__ import annotations

from typing import List, Tuple


def _solve(A: List[List[float]], b: List[float]) -> List[float]:
    """Solve A x = b by Gaussian elimination with partial pivoting."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot][col]) < 1e-12:
            raise ValueError("Singular system")
        M[col], M[pivot] = M[pivot], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))) / M[r][r]
    return x


class RidgeRegression:
    """Ridge regression on standardized features with an intercept."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.weights: List[float] = []
        self.intercept = 0.0
        self._means: List[float] = []
        self._stds: List[float] = []

    def _standardize(self, X: List[List[float]]) -> List[List[float]]:
        return [
            [(row[j] - self._means[j]) / self._stds[j] for j in range(len(row))]
            for row in X
        ]

    def fit(self, X: List[List[float]], y: List[float]) -> "RidgeRegression":
        n, p = len(X), len(X[0])
        self._means = [sum(row[j] for row in X) / n for j in range(p)]
        self._stds = []
        for j in range(p):
            var = sum((row[j] - self._means[j]) ** 2 for row in X) / n
            self._stds.append(var ** 0.5 or 1.0)
        Z = self._standardize(X)
        ymean = sum(y) / n
        yc = [v - ymean for v in y]

        # (Z'Z + alpha I) w = Z'y
        A = [[sum(Z[i][j] * Z[i][k] for i in range(n)) for k in range(p)] for j in range(p)]
        for j in range(p):
            A[j][j] += self.alpha
        b = [sum(Z[i][j] * yc[i] for i in range(n)) for j in range(p)]
        self.weights = _solve(A, b)
        self.intercept = ymean
        return self

    def predict(self, X: List[List[float]]) -> List[float]:
        Z = self._standardize(X)
        return [self.intercept + sum(w * z for w, z in zip(self.weights, row)) for row in Z]


def r_squared(y_true: List[float], y_pred: List[float]) -> float:
    mean = sum(y_true) / len(y_true)
    ss_tot = sum((v - mean) ** 2 for v in y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    return 1 - ss_res / ss_tot if ss_tot else 0.0


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


def kfold_alpha_search(
    X: List[List[float]], y: List[float], alphas: List[float], k: int = 5
) -> Tuple[float, float]:
    """Pick the ridge alpha with the best k-fold cross-validated R^2."""
    n = len(X)
    best = (alphas[0], float("-inf"))
    for alpha in alphas:
        scores = []
        for fold in range(k):
            test_idx = set(range(fold, n, k))
            Xtr = [X[i] for i in range(n) if i not in test_idx]
            ytr = [y[i] for i in range(n) if i not in test_idx]
            Xte = [X[i] for i in range(n) if i in test_idx]
            yte = [y[i] for i in range(n) if i in test_idx]
            model = RidgeRegression(alpha).fit(Xtr, ytr)
            scores.append(r_squared(yte, model.predict(Xte)))
        avg = sum(scores) / len(scores)
        if avg > best[1]:
            best = (alpha, avg)
    return best
