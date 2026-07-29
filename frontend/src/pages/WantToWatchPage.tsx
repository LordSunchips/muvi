import { useEffect, useState } from "react";
import { api } from "../api/client";
import { MoviePoster } from "../components/MoviePoster";
import { RankingModal } from "../components/RankingModal";
import type { Movie, Rank } from "../types";

export function WantToWatchPage() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rankingMovie, setRankingMovie] = useState<Movie | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await api.get<Movie[]>("/api/want-to-watch");
      setMovies(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function remove(movie: Movie) {
    await api.delete(`/api/want-to-watch/${movie.id}`);
    setMovies((prev) => prev.filter((m) => m.id !== movie.id));
  }

  return (
    <div className="page">
      <h1>Want to watch</h1>
      {error && <p className="error-text">{error}</p>}
      {loading && <p className="muted">Loading...</p>}
      {!loading && movies.length === 0 && (
        <p className="muted">Nothing here yet. Search for a movie and add it to your watchlist.</p>
      )}
      <div className="movie-grid">
        {movies.map((movie) => (
          <div className="movie-tile" key={movie.id}>
            <MoviePoster posterPath={movie.poster_path} title={movie.title} size="md" />
            <h3>{movie.title}</h3>
            <p className="muted small">{movie.year}</p>
            <div className="movie-tile-actions">
              <button className="secondary-button" onClick={() => remove(movie)}>
                Remove
              </button>
              <button className="primary-button" onClick={() => setRankingMovie(movie)}>
                I watched this
              </button>
            </div>
          </div>
        ))}
      </div>

      {rankingMovie && (
        <RankingModal
          movie={rankingMovie}
          onClose={() => setRankingMovie(null)}
          onComplete={(rank: Rank) => {
            setMovies((prev) => prev.filter((m) => m.id !== rankingMovie.id));
            void rank;
          }}
        />
      )}
    </div>
  );
}
