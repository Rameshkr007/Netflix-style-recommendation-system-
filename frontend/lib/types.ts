export interface Movie {
  id: number;
  title: string;
  genres: string; // "Action|Drama"
  year: number | null;
  director: string | null;
  cast: string | null;
  content_type: "movie" | "tv_show" | "anime" | "documentary";
  runtime_minutes: number | null;
  poster_url: string | null;
  synopsis: string | null;
}

export interface RecommendationItem {
  movie: Movie;
  score: number;
  reason: string;
  source: "hybrid" | "content" | "collaborative" | "popularity";
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "admin";
  favorite_genres: string | null;
  created_at: string;
}

export interface TasteDNA {
  genre_breakdown: Record<string, { percentage: number; avg_rating_given: number }>;
  viewing_personality: string;
  total_rated: number;
}

export interface ChatResponse {
  reply: string;
  intent: string;
  movies: Movie[];
}

export function genreList(genres: string): string[] {
  return genres.split("|").filter(Boolean);
}
