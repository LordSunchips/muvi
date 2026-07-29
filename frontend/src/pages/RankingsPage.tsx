import { useEffect, useState } from "react";
import { api } from "../api/client";
import { MoviePoster } from "../components/MoviePoster";
import { ScoreBadge, rowTierClass } from "../components/ScoreBadge";
import type { Rank } from "../types";

export function RankingsPage() {
  const [ranks, setRanks] = useState<Rank[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const res = await api.get<Rank[]>("/api/rankings");
      setRanks(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rankings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function removeRank(rank: Rank) {
    if (!confirm(`Remove "${rank.movie.title}" from your rankings?`)) return;
    await api.delete(`/api/rankings/${rank.id}`);
    setRanks((prev) => prev.filter((r) => r.id !== rank.id));
  }

  return (
    <div className="page">
      <h1>Your rankings</h1>
      {error && <p className="error-text">{error}</p>}
      {loading && <p className="muted">Loading...</p>}
      {!loading && ranks.length === 0 && (
        <p className="muted">You haven't ranked any movies yet. Head to Search to rank your first one.</p>
      )}
      <ol className="rank-list">
        {ranks.map((rank, i) => (
          <li className={`rank-row ${rowTierClass(rank.tier)}`} key={rank.id}>
            <span className="rank-position">{i + 1}</span>
            <MoviePoster posterPath={rank.movie.poster_path} title={rank.movie.title} size="sm" />
            <div className="rank-info">
              <strong>{rank.movie.title}</strong>
              <span className="muted small">
                {rank.movie.year} {rank.movie.director && `· ${rank.movie.director}`}
              </span>
              {rank.note && <span className="rank-note">"{rank.note}"</span>}
            </div>
            <ScoreBadge score={rank.score} tier={rank.tier} />
            <button className="link-button" onClick={() => removeRank(rank)}>
              remove
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
