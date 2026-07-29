import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { MoviePoster } from "../components/MoviePoster";
import { ScoreBadge } from "../components/ScoreBadge";
import type { FeedItem } from "../types";

export function FeedPage() {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<FeedItem[]>("/api/feed")
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load feed"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h1>Friend activity</h1>
      {error && <p className="error-text">{error}</p>}
      {loading && <p className="muted">Loading...</p>}
      {!loading && items.length === 0 && (
        <p className="muted">
          Nothing yet. Follow some friends from the <Link to="/friends">Friends</Link> page to see what they've been
          ranking.
        </p>
      )}
      <ul className="feed-list">
        {items.map((item) => (
          <li className="feed-row" key={item.id}>
            <MoviePoster posterPath={item.movie.poster_path} title={item.movie.title} size="sm" />
            <div className="rank-info">
              <span>
                <Link to={`/profile/${item.user.id}`}>
                  <strong>{item.user.display_name}</strong>
                </Link>{" "}
                ranked <strong>{item.movie.title}</strong>
              </span>
              {item.note && <span className="rank-note">"{item.note}"</span>}
              <span className="muted small">{new Date(item.created_at).toLocaleDateString()}</span>
            </div>
            <ScoreBadge score={item.score} tier={item.tier} />
          </li>
        ))}
      </ul>
    </div>
  );
}
