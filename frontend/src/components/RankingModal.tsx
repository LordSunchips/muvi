import { useState } from "react";
import { api } from "../api/client";
import type { Movie, Rank, RankingSessionState, Tier } from "../types";
import { MoviePoster } from "./MoviePoster";
import { ScoreBadge } from "./ScoreBadge";

interface Props {
  movie: Pick<Movie, "tmdb_id" | "title" | "year" | "poster_path">;
  onClose: () => void;
  onComplete: (rank: Rank) => void;
}

const TIER_OPTIONS: { tier: Tier; label: string; emoji: string; hint: string }[] = [
  { tier: "loved", label: "Loved it", emoji: "😍", hint: "This was great" },
  { tier: "liked", label: "Liked it", emoji: "🙂", hint: "It was fine" },
  { tier: "disliked", label: "Didn't like it", emoji: "🙁", hint: "Not for me" },
];

export function RankingModal({ movie, onClose, onComplete }: Props) {
  const [session, setSession] = useState<RankingSessionState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function pickTier(tier: Tier) {
    if (!movie.tmdb_id) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.post<RankingSessionState>("/api/rankings/sessions", {
        tmdb_id: movie.tmdb_id,
        tier,
      });
      setSession(res);
      if (res.done && res.result) {
        onComplete(res.result);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function answer(winner: "new" | "existing") {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.post<RankingSessionState>(`/api/rankings/sessions/${session.session_id}/answer`, {
        winner,
      });
      setSession(res);
      if (res.done && res.result) {
        onComplete(res.result);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const showResult = session?.done && session.result;
  const showDuel = session && !session.done && session.comparison_movie;
  const showTierPicker = !session;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        {showTierPicker && (
          <>
            <div className="modal-header">
              <MoviePoster posterPath={movie.poster_path} title={movie.title} size="md" />
              <div>
                <h2>{movie.title}</h2>
                <p className="muted">{movie.year}</p>
              </div>
            </div>
            <h3>How did you like it?</h3>
            <div className="tier-picker">
              {TIER_OPTIONS.map((opt) => (
                <button
                  key={opt.tier}
                  className={`tier-button tier-button-${opt.tier}`}
                  disabled={busy}
                  onClick={() => pickTier(opt.tier)}
                >
                  <span className="tier-emoji">{opt.emoji}</span>
                  <span>{opt.label}</span>
                  <span className="muted small">{opt.hint}</span>
                </button>
              ))}
            </div>
          </>
        )}

        {showDuel && session.comparison_movie && (
          <>
            <h3>Which was better?</h3>
            <p className="muted small">
              Comparison {session.comparisons_made + 1} of ~{session.total_comparisons_estimate}
            </p>
            <div className="duel-grid">
              <button className="duel-option" disabled={busy} onClick={() => answer("new")}>
                <MoviePoster posterPath={movie.poster_path} title={movie.title} size="lg" />
                <span>{movie.title}</span>
              </button>
              <div className="duel-vs">VS</div>
              <button className="duel-option" disabled={busy} onClick={() => answer("existing")}>
                <MoviePoster posterPath={session.comparison_movie.poster_path} title={session.comparison_movie.title} size="lg" />
                <span>{session.comparison_movie.title}</span>
              </button>
            </div>
          </>
        )}

        {showResult && session.result && (
          <div className="result-screen">
            <MoviePoster posterPath={session.result.movie.poster_path} title={session.result.movie.title} size="lg" />
            <h2>{session.result.movie.title}</h2>
            <ScoreBadge score={session.result.score} tier={session.result.tier} />
            <p className="muted">has been added to your rankings</p>
            <button className="primary-button" onClick={onClose}>
              Done
            </button>
          </div>
        )}

        {error && <p className="error-text">{error}</p>}
      </div>
    </div>
  );
}
