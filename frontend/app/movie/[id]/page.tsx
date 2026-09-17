"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Star, Plus, Check, Clock } from "lucide-react";
import { Header } from "@/components/Header";
import { MovieRail } from "@/components/MovieRail";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { Movie } from "@/lib/types";
import { genreList } from "@/lib/types";

export default function MovieDetailPage() {
  const params = useParams();
  const movieId = Number(params.id);
  const { user } = useAuth();

  const [movie, setMovie] = useState<Movie | null>(null);
  const [similar, setSimilar] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [myRating, setMyRating] = useState<number | null>(null);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [inWatchlist, setInWatchlist] = useState(false);
  const [ratingSaved, setRatingSaved] = useState(false);

  useEffect(() => {
    if (!movieId) return;
    setLoading(true);
    Promise.all([
      api.getMovie(movieId),
      api.similarMovies(movieId, 12).catch(() => []),
    ])
      .then(([movieRes, similarRes]) => {
        setMovie(movieRes);
        setSimilar(similarRes);
      })
      .catch(() => setMovie(null))
      .finally(() => setLoading(false));
  }, [movieId]);

  useEffect(() => {
    if (!user || !movieId) return;
    api.myWatchlist().then((items) => setInWatchlist(items.some((m) => m.id === movieId))).catch(() => {});
    // log a watch-history event on view, marking it as "started" -- a fuller
    // build would tie watch_time_seconds to an actual player
    api.logWatchHistory({ movie_id: movieId, watch_time_seconds: 0, completed: false, device_type: "desktop" }).catch(() => {});
  }, [user, movieId]);

  async function handleRate(value: number) {
    if (!user) return;
    setMyRating(value);
    try {
      await api.rateMovie(movieId, value);
      setRatingSaved(true);
      setTimeout(() => setRatingSaved(false), 2000);
    } catch {
      /* no-op */
    }
  }

  async function handleWatchlistToggle() {
    if (!user) return;
    try {
      if (inWatchlist) {
        await api.removeFromWatchlist(movieId);
      } else {
        await api.addToWatchlist(movieId);
      }
      setInWatchlist((prev) => !prev);
    } catch {
      /* no-op */
    }
  }

  if (loading) {
    return (
      <div className="flex-1">
        <Header />
        <div className="mx-auto max-w-5xl px-6 sm:px-10 py-16">
          <div className="skeleton h-10 w-2/3 rounded-lg mb-4" />
          <div className="skeleton h-4 w-1/3 rounded-lg mb-8" />
          <div className="skeleton h-32 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="flex-1">
        <Header />
        <div className="mx-auto max-w-5xl px-6 sm:px-10 py-16 text-[var(--color-text-muted)]">
          We couldn&apos;t find that title.
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1">
      <Header />

      <section className="relative">
        {movie.poster_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={movie.poster_url}
            alt=""
            aria-hidden="true"
            className="absolute inset-0 h-[420px] w-full object-cover opacity-25"
          />
        )}
        <div className="absolute inset-0 h-[420px] bg-gradient-to-t from-[var(--color-bg)] via-[var(--color-bg)]/70 to-[var(--color-bg)]/20" />

        <div className="relative mx-auto max-w-5xl px-6 sm:px-10 pt-16 pb-10">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <span className="text-xs uppercase tracking-[0.2em] text-[var(--color-red-accent)]">
              {movie.content_type.replace("_", " ")}
            </span>
            <h1 className="font-[family-name:var(--font-display)] text-4xl sm:text-5xl tracking-wide mt-2 mb-3">
              {movie.title.replace(/\s*\(\d{4}\)$/, "")}
            </h1>
            <div className="flex items-center gap-3 text-sm text-[var(--color-text-muted)] mb-4">
              {movie.year && <span>{movie.year}</span>}
              {movie.runtime_minutes && (
                <span className="flex items-center gap-1">
                  <Clock size={13} /> {movie.runtime_minutes} min
                </span>
              )}
              <span>{genreList(movie.genres).join(" • ")}</span>
            </div>

            {movie.synopsis && (
              <p className="max-w-2xl text-[var(--color-text-muted)] leading-relaxed mb-6">{movie.synopsis}</p>
            )}

            <div className="flex flex-wrap items-center gap-6 mb-6">
              {user && (
                <div>
                  <p className="text-xs text-[var(--color-text-dim)] mb-1.5">Your rating</p>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((star) => {
                      const filled = (hoverRating ?? myRating ?? 0) >= star;
                      return (
                        <button
                          key={star}
                          onMouseEnter={() => setHoverRating(star)}
                          onMouseLeave={() => setHoverRating(null)}
                          onClick={() => handleRate(star)}
                          aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
                          className="transition-transform hover:scale-110"
                        >
                          <Star
                            size={22}
                            className={filled ? "text-[var(--color-red)]" : "text-[var(--color-text-dim)]"}
                            fill={filled ? "currentColor" : "none"}
                            style={filled ? { filter: "drop-shadow(0 0 6px rgba(229,9,20,0.65))" } : undefined}
                          />
                        </button>
                      );
                    })}
                    {ratingSaved && <span className="ml-2 text-xs text-[var(--color-red-accent)]">Saved!</span>}
                  </div>
                </div>
              )}

              {user && (
                <button
                  onClick={handleWatchlistToggle}
                  className="glass flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium hover:border-[var(--color-red)] transition-colors"
                >
                  {inWatchlist ? <Check size={16} className="text-[var(--color-red)]" /> : <Plus size={16} />}
                  {inWatchlist ? "In your list" : "Add to list"}
                </button>
              )}
            </div>

            {(movie.director || movie.cast) && (
              <div className="text-sm text-[var(--color-text-muted)] space-y-1">
                {movie.director && (
                  <p>
                    <span className="text-[var(--color-text-dim)]">Director: </span>
                    {movie.director}
                  </p>
                )}
                {movie.cast && (
                  <p>
                    <span className="text-[var(--color-text-dim)]">Cast: </span>
                    {movie.cast}
                  </p>
                )}
              </div>
            )}
          </motion.div>
        </div>
      </section>

      <div className="sprocket-divider my-2" />

      <div className="pb-16">
        <MovieRail title="Because you watched this" movies={similar} />
      </div>
    </div>
  );
}
