"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Search as SearchIcon } from "lucide-react";
import { Header } from "@/components/Header";
import { MovieCard } from "@/components/MovieCard";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { Movie } from "@/lib/types";

function SearchContent() {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<Movie[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [watchlistIds, setWatchlistIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!user) return;
    api.myWatchlist().then((items) => setWatchlistIds(new Set(items.map((m) => m.id)))).catch(() => {});
  }, [user]);

  // Debounced autocomplete suggestions as the user types
  useEffect(() => {
    const handle = setTimeout(() => {
      if (!query.trim()) {
        setSuggestions([]);
        return;
      }
      api.suggestions(query).then(setSuggestions).catch(() => setSuggestions([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [query]);

  // Run the actual search whenever the URL's ?q= changes (covers header search + this page's form)
  useEffect(() => {
    const q = searchParams.get("q");
    if (!q) return;
    setQuery(q);
    setLoading(true);
    api
      .search(q, 30)
      .then(setResults)
      .catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [searchParams]);

  function runSearch(q: string) {
    if (!q.trim()) return;
    router.push(`/search?q=${encodeURIComponent(q.trim())}`);
    setSuggestions([]);
  }

  async function handleAddToWatchlist(movieId: number) {
    if (!user) return;
    const inList = watchlistIds.has(movieId);
    try {
      if (inList) {
        await api.removeFromWatchlist(movieId);
        setWatchlistIds((prev) => {
          const next = new Set(prev);
          next.delete(movieId);
          return next;
        });
      } else {
        await api.addToWatchlist(movieId);
        setWatchlistIds((prev) => new Set(prev).add(movieId));
      }
    } catch {
      /* no-op */
    }
  }

  return (
    <div className="flex-1">
      <Header />

      <div className="mx-auto max-w-7xl px-6 sm:px-10 py-10">
        <div className="relative mb-8 max-w-xl">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              runSearch(query);
            }}
            className="glass flex items-center gap-2 rounded-full px-4 py-3 border border-transparent transition-colors focus-within:border-[var(--color-red)] focus-within:shadow-[0_0_0_3px_rgba(229,9,20,0.18)]"
          >
            <SearchIcon size={18} className="text-[var(--color-text-dim)] shrink-0" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by title, actor, director, or genre…"
              className="w-full bg-transparent text-sm outline-none placeholder:text-[var(--color-text-dim)]"
              autoFocus
            />
          </form>

          <AnimatePresence>
            {suggestions.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.15 }}
                className="glass-strong absolute left-0 right-0 top-full mt-2 overflow-hidden rounded-xl z-20 border border-[var(--color-border-strong)]"
              >
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => runSearch(s)}
                    className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left text-sm hover:bg-[var(--color-red)]/10 hover:text-[var(--color-red-accent)] transition-colors"
                  >
                    <SearchIcon size={13} className="text-[var(--color-text-dim)] shrink-0" />
                    {s}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="skeleton aspect-[2/3] rounded-xl" />
            ))}
          </div>
        ) : results.length > 0 ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-6">
            {results.map((movie) => (
              <MovieCard
                key={movie.id}
                movie={movie}
                onAddToWatchlist={user ? handleAddToWatchlist : undefined}
                inWatchlist={watchlistIds.has(movie.id)}
              />
            ))}
          </div>
        ) : searchParams.get("q") ? (
          <p className="text-[var(--color-text-muted)]">
            No matches for &ldquo;{searchParams.get("q")}&rdquo;. Try a different title, actor, or genre.
          </p>
        ) : (
          <p className="text-[var(--color-text-muted)]">Start typing to search the catalog.</p>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={null}>
      <SearchContent />
    </Suspense>
  );
}
