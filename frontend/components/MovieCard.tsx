"use client";

import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { Play, Plus, Check, Info, Star } from "lucide-react";
import Link from "next/link";
import type { Movie } from "@/lib/types";
import { genreList } from "@/lib/types";

interface MovieCardProps {
  movie: Movie;
  reason?: string;
  onAddToWatchlist?: (movieId: number) => void;
  inWatchlist?: boolean;
}

export function MovieCard({ movie, reason, onAddToWatchlist, inWatchlist }: MovieCardProps) {
  const [hovered, setHovered] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = cardRef.current?.getBoundingClientRect();
    if (!rect) return;
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: py * -6, y: px * 8 });
  }

  return (
    <motion.div
      ref={cardRef}
      className="group relative shrink-0 w-[180px] sm:w-[210px]"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setTilt({ x: 0, y: 0 });
      }}
      onMouseMove={handleMouseMove}
      style={{ perspective: 800 }}
    >
      <motion.div
        animate={{
          rotateX: tilt.x,
          rotateY: tilt.y,
          scale: hovered ? 1.08 : 1,
          zIndex: hovered ? 30 : 1,
          boxShadow: hovered
            ? "0 0 0 1px rgba(229,9,20,0.45), 0 20px 50px rgba(229,9,20,0.3), 0 8px 24px rgba(0,0,0,0.6)"
            : "0 0 0 1px rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.45)",
        }}
        transition={{ type: "spring", stiffness: 260, damping: 20 }}
        className="relative rounded-xl overflow-hidden bg-[var(--color-card)] border border-[var(--color-border)]"
        style={{ transformStyle: "preserve-3d" }}
      >
        <Link href={`/movie/${movie.id}`} className="block">
          <div className="relative aspect-[2/3] bg-[var(--color-bg-elevated)] overflow-hidden">
            {movie.poster_url ? (
              <motion.img
                src={movie.poster_url}
                alt={movie.title}
                animate={{ scale: hovered ? 1.1 : 1 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="h-full w-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-[var(--color-text-dim)] text-xs px-3 text-center">
                {movie.title}
              </div>
            )}
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/90 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-3">
              <p className="font-[family-name:var(--font-display)] text-base leading-tight tracking-wide line-clamp-2">
                {movie.title}
              </p>
            </div>
          </div>
        </Link>

        {hovered && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.15 }}
            className="p-3 space-y-2"
          >
            <div className="flex items-center gap-2">
              <Link
                href={`/movie/${movie.id}`}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-red)] text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_14px_rgba(229,9,20,0.7)] transition-all"
                aria-label="View details"
              >
                <Play size={14} fill="currentColor" />
              </Link>
              {onAddToWatchlist && (
                <button
                  onClick={() => onAddToWatchlist(movie.id)}
                  className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--color-border-strong)] hover:border-[var(--color-red)] transition-colors"
                  aria-label={inWatchlist ? "In your list" : "Add to list"}
                >
                  {inWatchlist ? <Check size={14} className="text-[var(--color-red-accent)]" /> : <Plus size={14} />}
                </button>
              )}
              <Link
                href={`/movie/${movie.id}`}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--color-border-strong)] hover:border-[var(--color-red)] transition-colors ml-auto"
                aria-label="More info"
              >
                <Info size={14} />
              </Link>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-dim)]">
              {movie.year && <span>{movie.year}</span>}
              {movie.content_type !== "movie" && (
                <span className="rounded border border-[var(--color-border-strong)] px-1.5 py-0.5 uppercase text-[10px]">
                  {movie.content_type.replace("_", " ")}
                </span>
              )}
            </div>
            <p className="text-[11px] text-[var(--color-text-muted)] line-clamp-1">
              {genreList(movie.genres).join(" • ")}
            </p>
            {reason && (
              <div className="flex items-start gap-1.5 pt-1 border-t border-[var(--color-border)]">
                <Star size={11} className="text-[var(--color-red-accent)] mt-0.5 shrink-0" />
                <p className="text-[11px] text-[var(--color-red-accent)]/90 line-clamp-2">{reason}</p>
              </div>
            )}
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}
