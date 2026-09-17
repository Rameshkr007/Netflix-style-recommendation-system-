import type { ChatResponse, Movie, RecommendationItem, TasteDNA, User } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const TOKEN_KEY = "aperture_token";
const REFRESH_KEY = "aperture_refresh_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) { window.localStorage.setItem(TOKEN_KEY, token); }
export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}
export function setRefreshToken(token: string) { window.localStorage.setItem(REFRESH_KEY, token); }
export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  // Auto-refresh on 401
  if (res.status === 401 && retry) {
    const rt = getRefreshToken();
    if (rt) {
      try {
        const rr = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (rr.ok) {
          const data = await rr.json();
          setToken(data.access_token);
          if (data.refresh_token) setRefreshToken(data.refresh_token);
          return request<T>(path, options, false);
        }
      } catch { /* fall through */ }
    }
    clearToken();
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try { const b = await res.json(); detail = b.detail || detail; } catch { /* */ }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  register: (p: { email: string; password: string; display_name: string; favorite_genres: string[] }) =>
    request<{ access_token: string; refresh_token?: string }>("/auth/register", { method: "POST", body: JSON.stringify(p) }),
  login: (p: { email: string; password: string }) =>
    request<{ access_token: string; refresh_token?: string }>("/auth/login", { method: "POST", body: JSON.stringify(p) }),
  googleLogin: (id_token: string) =>
    request<{ access_token: string; refresh_token?: string }>("/auth/google", { method: "POST", body: JSON.stringify({ id_token }) }),
  me: () => request<User>("/auth/me"),

  listMovies: (params: { genre?: string; region?: string; content_type?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.genre) qs.set("genre", params.genre);
    if (params.region) qs.set("region", params.region);
    if (params.content_type) qs.set("content_type", params.content_type);
    qs.set("limit", String(params.limit ?? 24));
    return request<Movie[]>(`/movies?${qs.toString()}`);
  },
  getMovie: (id: number) => request<Movie>(`/movies/${id}`),
  similarMovies: (id: number, topK = 10) => request<Movie[]>(`/movies/${id}/similar?top_k=${topK}`),
  rateMovie: (movie_id: number, rating: number) =>
    request<unknown>("/movies/rate", { method: "POST", body: JSON.stringify({ movie_id, rating }) }),
  addToWatchlist: (movie_id: number) =>
    request<unknown>("/movies/watchlist", { method: "POST", body: JSON.stringify({ movie_id }) }),
  removeFromWatchlist: (movie_id: number) =>
    request<unknown>(`/movies/watchlist/${movie_id}`, { method: "DELETE" }),
  myWatchlist: () => request<Movie[]>("/movies/me/watchlist"),
  logWatchHistory: (p: { movie_id: number; watch_time_seconds: number; completed: boolean; device_type: string }) =>
    request<unknown>("/movies/watch-history", { method: "POST", body: JSON.stringify(p) }),

  forMe: (topK = 12) => request<RecommendationItem[]>(`/recommendations/for-me?top_k=${topK}`),
  moodRecommend: (mood_text: string) =>
    request<Movie[]>("/recommendations/mood", { method: "POST", body: JSON.stringify({ mood_text }) }),
  trending: (limit = 20) => request<Movie[]>(`/recommendations/trending?limit=${limit}`),
  tasteDna: () => request<TasteDNA>("/recommendations/taste-dna"),

  search: (q: string, topK = 20) => request<Movie[]>(`/search?q=${encodeURIComponent(q)}&top_k=${topK}`),
  suggestions: (q: string) => request<string[]>(`/search/suggestions?q=${encodeURIComponent(q)}`),

  chat: (message: string) =>
    request<ChatResponse>("/assistant/chat", { method: "POST", body: JSON.stringify({ message }) }),

  adminOverview: () => request<{
    total_users: number; total_titles: number; total_ratings: number;
    total_watch_events: number; total_watch_hours: number; average_rating: number;
  }>("/admin/analytics/overview"),
  adminEngagement: (days = 14) =>
    request<{ date: string; watch_events: number; watch_hours: number }[]>(
      `/admin/analytics/engagement-by-day?days=${days}`),
  adminTopSearches: (limit = 15) =>
    request<{ query: string; count: number }[]>(`/admin/analytics/top-search-queries?limit=${limit}`),
  adminAccuracy: (k = 10) =>
    request<{ rmse?: number; mae?: number; precision_at_10?: number; recall_at_10?: number;
      ndcg_at_10?: number; n_users_evaluated?: number; error?: string; }>(
      `/admin/analytics/recommendation-accuracy?k=${k}`),
  adminRefreshModel: () =>
    request<{ status: string; is_ready: boolean }>("/admin/model/refresh", { method: "POST" }),  createMovie: (movie: {
    title: string;
    genres: string;
    year?: number | null;
    director?: string | null;
    cast?: string | null;
    content_type?: string;
    runtime_minutes?: number | null;
    poster_url?: string | null;
    synopsis?: string | null;
  }) =>
    request<Movie>("/admin/movies", {
      method: "POST",
      body: JSON.stringify(movie),
    }),};

export { ApiError };
