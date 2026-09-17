"use client";

import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { MovieCard } from "./MovieCard";
import type { Movie, RecommendationItem } from "@/lib/types";

interface MovieRailProps {
  title: string;
  subtitle?: string;
  movies?: Movie[];
  recommendations?: RecommendationItem[];
  loading?: boolean;
  onAddToWatchlist?: (movieId: number) => void;
  watchlistIds?: Set<number>;
}

export function MovieRail({
  title,
  subtitle,
  movies,
  recommendations,
  loading,
  onAddToWatchlist,
  watchlistIds,
}: MovieRailProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  function scroll(dir: "left" | "right") {
    scrollRef.current?.scrollBy({ left: dir === "left" ? -640 : 640, behavior: "smooth" });
  }

  const items = recommendations
    ? recommendations.map((r) => ({ movie: r.movie, reason: r.reason }))
    : (movies ?? []).map((m) => ({ movie: m, reason: undefined }));

  if (!loading && items.length === 0) return null;

  return (
    <section className="relative py-3">
      <div className="mb-3 px-6 sm:px-10">
        <h2 className="font-[family-name:var(--font-display)] text-xl tracking-wide">{title}</h2>
        {subtitle && <p className="text-xs text-[var(--color-text-dim)] mt-0.5">{subtitle}</p>}
      </div>

      <div className="group/rail relative">
        <button
          onClick={() => scroll("left")}
          className="absolute left-1 top-0 bottom-0 z-20 hidden w-10 items-center justify-center bg-gradient-to-r from-[var(--color-bg)] to-transparent text-[var(--color-text-muted)] hover:text-[var(--color-red-accent)] transition-colors group-hover/rail:flex"
          aria-label="Scroll left"
        >
          <ChevronLeft size={22} />
        </button>

        <div
          ref={scrollRef}
          className="rail-scroll flex gap-3 overflow-x-auto px-6 sm:px-10 pb-3 pt-1 scroll-smooth"
        >
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skeleton shrink-0 w-[180px] sm:w-[210px] aspect-[2/3] rounded-xl" />
              ))
            : items.map(({ movie, reason }) => (
                <MovieCard
                  key={movie.id}
                  movie={movie}
                  reason={reason}
                  onAddToWatchlist={onAddToWatchlist}
                  inWatchlist={watchlistIds?.has(movie.id)}
                />
              ))}
        </div>

        <button
          onClick={() => scroll("right")}
          className="absolute right-1 top-0 bottom-0 z-20 hidden w-10 items-center justify-center bg-gradient-to-l from-[var(--color-bg)] to-transparent text-[var(--color-text-muted)] hover:text-[var(--color-red-accent)] transition-colors group-hover/rail:flex"
          aria-label="Scroll right"
        >
          <ChevronRight size={22} />
        </button>
      </div>
    </section>
  );
}
