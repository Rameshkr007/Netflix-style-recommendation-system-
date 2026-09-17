"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { Bookmark } from "lucide-react";
import { Header } from "@/components/Header";
import { MovieCard } from "@/components/MovieCard";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { Movie } from "@/lib/types";

export default function WatchlistPage() {
  const { user, loading: authLoading } = useAuth();
  const [movies, setMovies] = useState<Movie[]>([]);
  const [dataLoading, setDataLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    setDataLoading(true);
    api
      .myWatchlist()
      .then(setMovies)
      .catch(() => setMovies([]))
      .finally(() => setDataLoading(false));
  }, [user]);

  const loading = authLoading || (Boolean(user) && dataLoading && movies.length === 0);

  async function handleRemove(movieId: number) {
    try {
      await api.removeFromWatchlist(movieId);
      setMovies((prev) => prev.filter((m) => m.id !== movieId));
    } catch {
      /* no-op */
    }
  }

  return (
    <div className="flex-1">
      <Header />
      <div className="mx-auto max-w-7xl px-6 sm:px-10 py-10">
        <div className="mb-8 flex items-center gap-2">
          <Bookmark size={20} className="text-[var(--color-red)]" />
          <h1 className="font-[family-name:var(--font-display)] text-2xl tracking-wide">My List</h1>
        </div>

        {!authLoading && !user ? (
          <p className="text-[var(--color-text-muted)]">
            <Link href="/login" className="text-[var(--color-red-accent)] hover:text-white">
              Sign in
            </Link>{" "}
            to build your watchlist.
          </p>
        ) : loading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton aspect-[2/3] rounded-xl" />
            ))}
          </div>
        ) : movies.length === 0 ? (
          <p className="text-[var(--color-text-muted)]">
            Nothing here yet. Add titles from anywhere you see the{" "}
            <span className="text-[var(--color-red-accent)]">+</span> button.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
            <AnimatePresence mode="popLayout">
              {movies.map((movie) => (
                <motion.div
                  key={movie.id}
                  layout
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85, transition: { duration: 0.2 } }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                >
                  <MovieCard movie={movie} onAddToWatchlist={handleRemove} inWatchlist />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
