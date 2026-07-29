import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { MoviePoster } from "../components/MoviePoster";
import { RankingModal } from "../components/RankingModal";
import type { MovieSearchResult, Rank } from "../types";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSearchResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [addedIds, setAddedIds] = useState<Set<number>>(new Set());
  const [rankingMovie, setRankingMovie] = useState<MovieSearchResult | null>(null);
  const [rankedIds, setRankedIds] = useState<Set<number>>(new Set());

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.get<MovieSearchResult[]>(`/api/movies/search?q=${encodeURIComponent(query)}`);
      setResults(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  async function addToWatchlist(movie: MovieSearchResult) {
    try {
      await api.post("/api/want-to-watch", { tmdb_id: movie.tmdb_id });
      setAddedIds((prev) => new Set(prev).add(movie.tmdb_id));
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setAddedIds((prev) => new Set(prev).add(movie.tmdb_id));
      } else {
        setError(err instanceof Error ? err.message : "Could not add to watchlist");
      }
    }
  }

  return (
    <div className="page">
      <h1>Search movies</h1>
      <form className="search-bar" onSubmit={handleSearch}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a movie title..."
          autoFocus
        />
        <button className="primary-button" type="submit" disabled={busy}>
          {busy ? "Searching..." : "Search"}
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}

      <div className="movie-grid">
        {results.map((movie) => (
          <div className="movie-tile" key={movie.tmdb_id}>
            <MoviePoster posterPath={movie.poster_path} title={movie.title} size="md" />
            <h3>{movie.title}</h3>
            <p className="muted small">{movie.year}</p>
            <p className="overview-clamp">{movie.overview}</p>
            <div className="movie-tile-actions">
              <button
                className="secondary-button"
                disabled={addedIds.has(movie.tmdb_id)}
                onClick={() => addToWatchlist(movie)}
              >
                {addedIds.has(movie.tmdb_id) ? "In watchlist" : "+ Watchlist"}
              </button>
              <button
                className="primary-button"
                disabled={rankedIds.has(movie.tmdb_id)}
                onClick={() => setRankingMovie(movie)}
              >
                {rankedIds.has(movie.tmdb_id) ? "Ranked" : "I watched this"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {results.length === 0 && !busy && (
        <p className="muted">
          Search for a movie to add it to your watchlist or rank it. Try “inception”, “godfather”, or “parasite”.
        </p>
      )}

      {rankingMovie && (
        <RankingModal
          movie={{
            tmdb_id: rankingMovie.tmdb_id,
            title: rankingMovie.title,
            year: rankingMovie.year,
            poster_path: rankingMovie.poster_path,
          }}
          onClose={() => setRankingMovie(null)}
          onComplete={(rank: Rank) => {
            setRankedIds((prev) => new Set(prev).add(rankingMovie.tmdb_id));
            setAddedIds((prev) => {
              const next = new Set(prev);
              next.delete(rankingMovie.tmdb_id);
              return next;
            });
            void rank;
          }}
        />
      )}
    </div>
  );
}
