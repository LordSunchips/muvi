from statistics import mean, median

from app.models import DisplayMetric, Ranking


def computed_score(
    rankings: list[Ranking],
    metric: DisplayMetric,
    genre_id: int | None = None,
) -> float | None:
    """Reduce a movie's ranking history to a single displayable score.

    Scope:
    - ``genre_id is None`` → consider only global rankings (rankings with ``genre_id is None``).
    - ``genre_id`` set → consider only rankings scoped to that genre. Falls back to global if the
      movie has no ranking in that genre, so genre-filtered library views aren't mostly empty for
      users who haven't done per-genre re-ranks yet.

    Rankings may be in any order — this function does not assume sorting. Returns ``None`` when
    no ranking in the chosen scope exists.
    """
    if genre_id is not None:
        genre_scoped = [r for r in rankings if r.genre_id == genre_id]
        if genre_scoped:
            return _reduce(genre_scoped, metric)
    global_scoped = [r for r in rankings if r.genre_id is None]
    if not global_scoped:
        return None
    return _reduce(global_scoped, metric)


def _reduce(rankings: list[Ranking], metric: DisplayMetric) -> float:
    scores = [r.score for r in rankings]
    if metric == DisplayMetric.MEAN:
        return round(mean(scores), 3)
    if metric == DisplayMetric.MEDIAN:
        return round(median(scores), 3)
    latest = max(rankings, key=lambda r: r.created_at)
    return latest.score
