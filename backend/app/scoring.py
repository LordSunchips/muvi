from statistics import mean, median

from app.models import DisplayMetric, Ranking


def computed_score(rankings: list[Ranking], metric: DisplayMetric) -> float | None:
    """Reduce a movie's ranking history to a single displayable score.

    Rankings may be passed in any order — this function does not assume sorting.
    Returns None when the movie has never been ranked.
    """
    if not rankings:
        return None
    scores = [r.score for r in rankings]
    if metric == DisplayMetric.MEAN:
        return round(mean(scores), 3)
    if metric == DisplayMetric.MEDIAN:
        return round(median(scores), 3)
    latest = max(rankings, key=lambda r: r.created_at)
    return latest.score
