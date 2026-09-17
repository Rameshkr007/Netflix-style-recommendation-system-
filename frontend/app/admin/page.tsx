"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users, Film, Star, Clock, TrendingUp, RefreshCw,
  BarChart2, Search, Shield, Activity, Zap, AlertCircle,
  CheckCircle, Database, Cpu, Eye
} from "lucide-react";
import { Header } from "@/components/Header";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────
interface Overview {
  total_users: number;
  total_titles: number;
  total_ratings: number;
  total_watch_events: number;
  total_watch_hours: number;
  average_rating: number;
}
interface EngagementDay {
  date: string;
  watch_events: number;
  watch_hours: number;
}
interface SearchQuery { query: string; count: number; }
interface AccuracyMetrics {
  rmse?: number; mae?: number;
  precision_at_10?: number; recall_at_10?: number; ndcg_at_10?: number;
  n_users_evaluated?: number; error?: string;
}

// ── Mini bar chart (no external lib needed) ───────────────────────────────
function MiniBarChart({ data, valueKey, label }: {
  data: EngagementDay[];
  valueKey: "watch_events" | "watch_hours";
  label: string;
}) {
  const values = data.map(d => d[valueKey]);
  const max = Math.max(...values, 1);
  return (
    <div>
      <p className="text-xs text-[var(--color-text-dim)] mb-2">{label}</p>
      <div className="flex items-end gap-1 h-16">
        {data.map((d, i) => {
          const pct = (d[valueKey] / max) * 100;
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
              <div
                className="w-full rounded-sm bg-[var(--color-red)]/60 group-hover:bg-[var(--color-red)] transition-all"
                style={{ height: `${Math.max(pct, 4)}%` }}
              />
              <div className="absolute bottom-full mb-1 hidden group-hover:block bg-[var(--color-card)] border border-[var(--color-border)] rounded px-2 py-1 text-xs whitespace-nowrap z-10">
                {d.date}: {d[valueKey].toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] text-[var(--color-text-dim)] mt-1">
        <span>{data[0]?.date?.slice(5)}</span>
        <span>{data[data.length - 1]?.date?.slice(5)}</span>
      </div>
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, color = "var(--color-red)" }: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-strong rounded-xl p-5 flex items-start gap-4"
    >
      <div className="rounded-lg p-2.5 shrink-0" style={{ background: `${color}22` }}>
        <Icon size={20} style={{ color }} />
      </div>
      <div>
        <p className="text-2xl font-bold">{typeof value === "number" ? value.toLocaleString() : value}</p>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{label}</p>
        {sub && <p className="text-xs text-[var(--color-text-dim)] mt-1">{sub}</p>}
      </div>
    </motion.div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────
export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [overview, setOverview] = useState<Overview | null>(null);
  const [engagement, setEngagement] = useState<EngagementDay[]>([]);
  const [topSearches, setTopSearches] = useState<SearchQuery[]>([]);
  const [accuracy, setAccuracy] = useState<AccuracyMetrics | null>(null);
  const [modelRefreshing, setModelRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "ml" | "search" | "engagement" | "movies">("overview");
  const [movieForm, setMovieForm] = useState({
    title: "",
    genres: "Drama|Action",
    year: new Date().getFullYear(),
    director: "",
    cast: "",
    content_type: "movie",
    runtime_minutes: 120,
    poster_url: "",
    synopsis: "",
  });
  const [movieSubmitting, setMovieSubmitting] = useState(false);

  // Redirect non-admins
  useEffect(() => {
    if (!authLoading && (!user || user.role !== "admin")) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  const loadData = useCallback(async () => {
    if (!user || user.role !== "admin") return;
    const [ov, eng, sq, acc] = await Promise.allSettled([
      api.adminOverview(),
      api.adminEngagement(14),
      api.adminTopSearches(15),
      api.adminAccuracy(10),
    ]);
    if (ov.status === "fulfilled") setOverview(ov.value);
    if (eng.status === "fulfilled") setEngagement(eng.value);
    if (sq.status === "fulfilled") setTopSearches(sq.value);
    if (acc.status === "fulfilled") setAccuracy(acc.value);
  }, [user]);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleModelRefresh() {
    setModelRefreshing(true);
    setRefreshMsg(null);
    try {
      const result = await api.adminRefreshModel();
      setRefreshMsg({ type: "ok", text: `Model refreshed! Ready: ${result.is_ready}` });
      await loadData();
    } catch {
      setRefreshMsg({ type: "err", text: "Refresh failed. Check backend logs." });
    } finally {
      setModelRefreshing(false);
    }
  }

  if (authLoading || !user) return null;
  if (user.role !== "admin") return null;

  const TABS = [
    { id: "overview", label: "Overview", icon: BarChart2 },
    { id: "ml", label: "ML Metrics", icon: Cpu },
    { id: "engagement", label: "Engagement", icon: Activity },
    { id: "search", label: "Search Analytics", icon: Search },
    { id: "movies", label: "Add Movies", icon: Film },
  ] as const;

  async function handleCreateMovie(e: React.FormEvent) {
    e.preventDefault();
    setMovieSubmitting(true);
    setRefreshMsg(null);

    try {
      const payload = {
        ...movieForm,
        genres: movieForm.genres.trim() || "Drama",
        title: movieForm.title.trim(),
        director: movieForm.director.trim() || null,
        cast: movieForm.cast.trim() || null,
        poster_url: movieForm.poster_url.trim() || null,
        synopsis: movieForm.synopsis.trim() || null,
      };

      if (!payload.title) throw new Error("Title is required");

      const created = await api.createMovie(payload);
      setRefreshMsg({ type: "ok", text: `Added movie: ${created.title}` });
      setMovieForm({
        title: "",
        genres: "Drama|Action",
        year: new Date().getFullYear(),
        director: "",
        cast: "",
        content_type: "movie",
        runtime_minutes: 120,
        poster_url: "",
        synopsis: "",
      });
      await loadData();
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Failed to add movie";
      setRefreshMsg({ type: "err", text: msg });
    } finally {
      setMovieSubmitting(false);
    }
  }

  return (
    <div className="flex-1">
      <Header />
      <div className="mx-auto max-w-7xl px-6 sm:px-10 py-8">

        {/* Page header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Shield size={22} className="text-[var(--color-red-accent)]" />
            <div>
              <h1 className="font-[family-name:var(--font-display)] text-2xl tracking-wide">
                Admin Dashboard
              </h1>
              <p className="text-xs text-[var(--color-text-dim)] mt-0.5">
                Platform analytics & model management
              </p>
            </div>
          </div>
          <button
            onClick={handleModelRefresh}
            disabled={modelRefreshing}
            className="flex items-center gap-2 rounded-lg bg-[var(--color-red)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_18px_rgba(229,9,20,0.4)] transition-all disabled:opacity-50"
          >
            <RefreshCw size={15} className={modelRefreshing ? "animate-spin" : ""} />
            {modelRefreshing ? "Refreshing..." : "Refresh ML Model"}
          </button>
        </div>

        {/* Refresh message */}
        <AnimatePresence>
          {refreshMsg && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`flex items-center gap-2 rounded-lg p-3 mb-4 text-sm ${
                refreshMsg.type === "ok"
                  ? "bg-green-500/10 border border-green-500/30 text-green-400"
                  : "bg-[var(--color-red)]/10 border border-[var(--color-red)]/30 text-[var(--color-red-accent)]"
              }`}
            >
              {refreshMsg.type === "ok"
                ? <CheckCircle size={16} />
                : <AlertCircle size={16} />
              }
              {refreshMsg.text}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tabs */}
        <div className="flex gap-1 p-1 glass rounded-xl mb-6 w-fit">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all ${
                activeTab === id
                  ? "bg-[var(--color-red)] text-white shadow-[0_0_14px_rgba(229,9,20,0.4)]"
                  : "text-[var(--color-text-muted)] hover:text-white"
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* Movies tab */}
        {activeTab === "movies" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="glass-strong rounded-xl p-6">
              <h2 className="font-semibold text-lg mb-4">Add a new title to the catalog</h2>
              <form onSubmit={handleCreateMovie} className="grid gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Title
                  <input
                    value={movieForm.title}
                    onChange={(e) => setMovieForm({ ...movieForm, title: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                    placeholder="Example: New Bollywood Blockbuster"
                    required
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Genres
                  <input
                    value={movieForm.genres}
                    onChange={(e) => setMovieForm({ ...movieForm, genres: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                    placeholder="Drama|Action|Comedy"
                    required
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Year
                  <input
                    type="number"
                    value={movieForm.year}
                    onChange={(e) => setMovieForm({ ...movieForm, year: Number(e.target.value) || new Date().getFullYear() })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Runtime (minutes)
                  <input
                    type="number"
                    value={movieForm.runtime_minutes}
                    onChange={(e) => setMovieForm({ ...movieForm, runtime_minutes: Number(e.target.value) || 120 })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Director
                  <input
                    value={movieForm.director}
                    onChange={(e) => setMovieForm({ ...movieForm, director: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Cast
                  <input
                    value={movieForm.cast}
                    onChange={(e) => setMovieForm({ ...movieForm, cast: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)]">
                  Content type
                  <select
                    value={movieForm.content_type}
                    onChange={(e) => setMovieForm({ ...movieForm, content_type: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                  >
                    <option value="movie">movie</option>
                    <option value="tv_show">tv_show</option>
                    <option value="anime">anime</option>
                    <option value="documentary">documentary</option>
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)] md:col-span-2">
                  Poster URL
                  <input
                    value={movieForm.poster_url}
                    onChange={(e) => setMovieForm({ ...movieForm, poster_url: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white"
                    placeholder="https://..."
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm text-[var(--color-text-muted)] md:col-span-2">
                  Synopsis
                  <textarea
                    value={movieForm.synopsis}
                    onChange={(e) => setMovieForm({ ...movieForm, synopsis: e.target.value })}
                    className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-white min-h-[120px]"
                    placeholder="Short description of the movie"
                  />
                </label>

                <div className="md:col-span-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={movieSubmitting}
                    className="rounded-lg bg-[var(--color-red)] px-5 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-red-hover)] disabled:opacity-60"
                  >
                    {movieSubmitting ? "Adding..." : "Add movie"}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        )}

        {/* Overview Tab */}
        {activeTab === "overview" && overview && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 col-span-full">
              <StatCard icon={Users}    label="Total Users"       value={overview.total_users} />
              <StatCard icon={Film}     label="Total Titles"      value={overview.total_titles} color="#448aff" />
              <StatCard icon={Star}     label="Total Ratings"     value={overview.total_ratings} color="#ffd700" />
              <StatCard icon={Eye}      label="Watch Events"      value={overview.total_watch_events} color="#00c853" />
              <StatCard icon={Clock}    label="Hours Watched"     value={overview.total_watch_hours} color="#bb44ff" />
              <StatCard icon={TrendingUp} label="Avg Rating"      value={overview.average_rating.toFixed(2) + " ⭐"} />
            </div>

            {/* System health */}
            <div className="glass-strong rounded-xl p-5">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <Database size={16} className="text-[var(--color-red-accent)]" />
                System Status
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label: "API", status: "Healthy", color: "#00c853" },
                  { label: "PostgreSQL", status: "Connected", color: "#00c853" },
                  { label: "Redis Cache", status: "Active", color: "#00c853" },
                  { label: "ML Model", status: "Loaded", color: "#00c853" },
                ].map(({ label, status, color }) => (
                  <div key={label} className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full animate-pulse" style={{ background: color }} />
                    <span className="text-sm text-[var(--color-text-muted)]">{label}</span>
                    <span className="text-xs ml-auto" style={{ color }}>{status}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* ML Metrics Tab */}
        {activeTab === "ml" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="glass-strong rounded-xl p-6">
              <h2 className="font-semibold mb-1 flex items-center gap-2">
                <Cpu size={16} className="text-[var(--color-red-accent)]" />
                Recommendation Model Performance
              </h2>
              <p className="text-xs text-[var(--color-text-dim)] mb-6">
                Offline evaluation on time-based test split (most recent 20% of ratings per user)
              </p>

              {accuracy?.error ? (
                <p className="text-[var(--color-text-muted)] text-sm">{accuracy.error}</p>
              ) : accuracy ? (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
                  {[
                    { label: "Precision@10", value: accuracy.precision_at_10, desc: "Relevant items in top 10", color: "#00c853" },
                    { label: "Recall@10", value: accuracy.recall_at_10, desc: "Coverage of relevant items", color: "#448aff" },
                    { label: "NDCG@10", value: accuracy.ndcg_at_10, desc: "Ranking quality", color: "#bb44ff" },
                    { label: "RMSE", value: accuracy.rmse, desc: "Rating prediction error", color: "#ffd700" },
                    { label: "MAE", value: accuracy.mae, desc: "Mean absolute error", color: "#ff8c00" },
                  ].map(({ label, value, desc, color }) => (
                    <div key={label} className="glass rounded-xl p-4 text-center">
                      <p className="text-2xl font-bold" style={{ color }}>
                        {value != null ? value.toFixed(4) : "—"}
                      </p>
                      <p className="text-xs font-medium mt-1">{label}</p>
                      <p className="text-[10px] text-[var(--color-text-dim)] mt-1">{desc}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-5 gap-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="skeleton h-24 rounded-xl" />
                  ))}
                </div>
              )}

              {accuracy && !accuracy.error && (
                <div className="mt-4 p-3 glass rounded-lg text-xs text-[var(--color-text-muted)]">
                  <strong className="text-[var(--color-red-accent)]">
                    Users evaluated: {accuracy.n_users_evaluated?.toLocaleString()}
                  </strong>
                  {" · "}
                  Model: Hybrid (SVD Collaborative Filtering + TF-IDF Content-Based, α=0.6)
                </div>
              )}
            </div>

            {/* Model info */}
            <div className="glass-strong rounded-xl p-5">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <Zap size={16} className="text-[var(--color-red-accent)]" />
                Model Architecture
              </h2>
              <div className="space-y-3">
                {[
                  { name: "Content-Based Filtering", detail: "TF-IDF on genres(3x) + director(2x) + cast + synopsis → Cosine similarity", badge: "Active" },
                  { name: "Collaborative Filtering", detail: "Truncated SVD (n_factors=30) on mean-centered user-item matrix", badge: "Active" },
                  { name: "Hybrid Blender", detail: "Weighted blend: 60% CF + 40% CB (α tunable per request for A/B testing)", badge: "Active" },
                  { name: "Neural Collaborative Filtering", detail: "GMF + MLP architecture (PyTorch) — available, not in default blend", badge: "Optional" },
                  { name: "Mood-Based NLP", detail: "Keyword + TF-IDF cosine similarity → genre mapping → content filter", badge: "Active" },
                ].map(({ name, detail, badge }) => (
                  <div key={name} className="flex items-start gap-3 p-3 glass rounded-lg">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full shrink-0 mt-0.5 ${
                      badge === "Active"
                        ? "bg-green-500/15 text-green-400 border border-green-500/30"
                        : "bg-[var(--color-border)] text-[var(--color-text-dim)]"
                    }`}>
                      {badge}
                    </span>
                    <div>
                      <p className="text-sm font-medium">{name}</p>
                      <p className="text-xs text-[var(--color-text-dim)] mt-0.5">{detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Engagement Tab */}
        {activeTab === "engagement" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            <div className="glass-strong rounded-xl p-5">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <Activity size={16} className="text-[var(--color-red-accent)]" />
                14-Day Engagement
              </h2>
              {engagement.length > 0 ? (
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                  <MiniBarChart data={engagement} valueKey="watch_events" label="Daily Watch Events" />
                  <MiniBarChart data={engagement} valueKey="watch_hours" label="Daily Watch Hours" />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-6">
                  {[0, 1].map(i => <div key={i} className="skeleton h-28 rounded-lg" />)}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Search Analytics Tab */}
        {activeTab === "search" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="glass-strong rounded-xl p-5">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <Search size={16} className="text-[var(--color-red-accent)]" />
                Top Search Queries
              </h2>
              {topSearches.length > 0 ? (
                <div className="space-y-2">
                  {topSearches.map(({ query, count }, i) => {
                    const maxCount = topSearches[0].count;
                    return (
                      <div key={query} className="flex items-center gap-3">
                        <span className="text-xs text-[var(--color-text-dim)] w-5 shrink-0">#{i + 1}</span>
                        <span className="text-sm w-40 truncate shrink-0">{query}</span>
                        <div className="flex-1 h-1.5 bg-[var(--color-surface)] rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(count / maxCount) * 100}%` }}
                            transition={{ delay: i * 0.04 }}
                            className="h-full bg-[var(--color-red)] rounded-full"
                          />
                        </div>
                        <span className="text-xs text-[var(--color-text-dim)] w-8 text-right shrink-0">
                          {count}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-[var(--color-text-muted)] text-sm">No search data yet.</p>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
