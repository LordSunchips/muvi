import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { User } from "../types";

export function FriendsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<User[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.get<User[]>(`/api/users/search?q=${encodeURIComponent(query)}`);
      setResults(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h1>Find friends</h1>
      <form className="search-bar" onSubmit={handleSearch}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by username or name..."
          autoFocus
        />
        <button className="primary-button" type="submit" disabled={busy}>
          {busy ? "Searching..." : "Search"}
        </button>
      </form>
      {error && <p className="error-text">{error}</p>}

      <ul className="user-list">
        {results.map((u) => (
          <li className="user-row" key={u.id}>
            <div className="avatar-circle small">{u.display_name[0]?.toUpperCase()}</div>
            <Link to={`/profile/${u.id}`}>
              <strong>{u.display_name}</strong> <span className="muted small">@{u.username}</span>
            </Link>
          </li>
        ))}
      </ul>
      {results.length === 0 && !busy && <p className="muted">Search to find people to follow.</p>}
    </div>
  );
}
