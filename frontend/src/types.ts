export type Tier = "loved" | "liked" | "disliked";

export interface User {
  id: number;
  username: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  created_at: string;
}

export interface UserProfile extends User {
  ranked_count: number;
  want_to_watch_count: number;
  followers_count: number;
  following_count: number;
  is_following: boolean;
}

export interface Movie {
  id: number;
  tmdb_id: number | null;
  title: string;
  year: number | null;
  poster_path: string;
  backdrop_path: string;
  overview: string;
  director: string;
  runtime: number | null;
  genres: string;
}

export interface MovieSearchResult {
  tmdb_id: number;
  title: string;
  year: number | null;
  poster_path: string;
  overview: string;
}

export interface Rank {
  id: number;
  movie: Movie;
  tier: Tier;
  score: number;
  note: string;
  created_at: string;
}

export interface RankingSessionState {
  session_id: number;
  done: boolean;
  comparison_movie: Movie | null;
  result: Rank | null;
  total_comparisons_estimate: number;
  comparisons_made: number;
}

export interface FeedItem {
  id: number;
  user: User;
  movie: Movie;
  tier: Tier;
  score: number;
  note: string;
  created_at: string;
}
