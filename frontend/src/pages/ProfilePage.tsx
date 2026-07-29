import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { MoviePoster } from "../components/MoviePoster";
import { ScoreBadge } from "../components/ScoreBadge";
import type { Rank, UserProfile } from "../types";

export function ProfilePage() {
  const { userId } = useParams();
  const { user: currentUser } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [ranks, setRanks] = useState<Rank[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [followBusy, setFollowBusy] = useState(false);

  const isSelf = currentUser?.id === Number(userId);

  async function load() {
    if (!userId) return;
    setLoading(true);
    setError("");
    try {
      const [profileRes, ranksRes] = await Promise.all([
        api.get<UserProfile>(`/api/users/${userId}`),
        api.get<Rank[]>(`/api/rankings/user/${userId}`),
      ]);
      setProfile(profileRes);
      setRanks(ranksRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [userId]);

  async function toggleFollow() {
    if (!profile) return;
    setFollowBusy(true);
    try {
      if (profile.is_following) {
        await api.delete(`/api/users/${profile.id}/follow`);
      } else {
        await api.post(`/api/users/${profile.id}/follow`);
      }
      setProfile({
        ...profile,
        is_following: !profile.is_following,
        followers_count: profile.followers_count + (profile.is_following ? -1 : 1),
      });
    } finally {
      setFollowBusy(false);
    }
  }

  if (loading) return <div className="page">Loading...</div>;
  if (error) return <div className="page error-text">{error}</div>;
  if (!profile) return null;

  return (
    <div className="page">
      <div className="profile-header">
        <div className="avatar-circle">{profile.display_name[0]?.toUpperCase()}</div>
        <div>
          <h1>{profile.display_name}</h1>
          <p className="muted">@{profile.username}</p>
          {profile.bio && <p>{profile.bio}</p>}
        </div>
        {!isSelf && (
          <button className={profile.is_following ? "secondary-button" : "primary-button"} disabled={followBusy} onClick={toggleFollow}>
            {profile.is_following ? "Following" : "Follow"}
          </button>
        )}
      </div>

      <div className="stat-row">
        <div className="stat">
          <strong>{profile.ranked_count}</strong>
          <span className="muted small">Ranked</span>
        </div>
        <div className="stat">
          <strong>{profile.want_to_watch_count}</strong>
          <span className="muted small">Watchlist</span>
        </div>
        <div className="stat">
          <strong>{profile.followers_count}</strong>
          <span className="muted small">Followers</span>
        </div>
        <div className="stat">
          <strong>{profile.following_count}</strong>
          <span className="muted small">Following</span>
        </div>
      </div>

      <h2>Rankings</h2>
      {ranks.length === 0 && <p className="muted">No rankings yet.</p>}
      <ol className="rank-list">
        {ranks.map((rank, i) => (
          <li className="rank-row" key={rank.id}>
            <span className="rank-position">{i + 1}</span>
            <MoviePoster posterPath={rank.movie.poster_path} title={rank.movie.title} size="sm" />
            <div className="rank-info">
              <strong>{rank.movie.title}</strong>
              <span className="muted small">{rank.movie.year}</span>
            </div>
            <ScoreBadge score={rank.score} tier={rank.tier} />
          </li>
        ))}
      </ol>
    </div>
  );
}
