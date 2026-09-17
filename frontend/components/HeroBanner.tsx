"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Info, Play } from "lucide-react";
import Link from "next/link";
import type { Movie } from "@/lib/types";
import { genreList } from "@/lib/types";

/* Lightweight canvas particle field -- ambient "film grain catching light"
   effect behind the hero, not a generic dot-network background. Particles
   drift slowly and connect into faint threads when close, echoing the
   "reasoning thread" motif used for recommendation explanations elsewhere. */
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = canvas.offsetWidth);
    let height = (canvas.height = canvas.offsetHeight);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const count = prefersReducedMotion ? 0 : 46;

    const particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      r: Math.random() * 1.6 + 0.4,
    }));

    let raf: number;
    function tick() {
      ctx!.clearRect(0, 0, width, height);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx!.fillStyle = "rgba(255, 59, 59, 0.55)";
        ctx!.fill();
      }
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < 110) {
            ctx!.beginPath();
            ctx!.moveTo(a.x, a.y);
            ctx!.lineTo(b.x, b.y);
            ctx!.strokeStyle = `rgba(229, 9, 20, ${0.14 * (1 - dist / 110)})`;
            ctx!.lineWidth = 0.6;
            ctx!.stroke();
          }
        }
      }
      raf = requestAnimationFrame(tick);
    }
    tick();

    function handleResize() {
      if (!canvas) return;
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    }
    window.addEventListener("resize", handleResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden="true" />;
}

export function HeroBanner({ movie }: { movie: Movie }) {
  return (
    <section className="relative h-[78vh] min-h-[460px] w-full overflow-hidden">
      <div className="absolute inset-0">
        {movie.poster_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={movie.poster_url}
            alt=""
            className="h-full w-full object-cover opacity-40 scale-110"
            aria-hidden="true"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-bg)] via-[var(--color-bg)]/60 to-[var(--color-bg)]/10" />
        <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-bg)]/95 via-[var(--color-bg)]/30 to-transparent" />
        {/* Cinematic spotlight + projector beam -- the signature hero atmosphere */}
        <div className="hero-spotlight" aria-hidden="true" />
        <div className="projector-beam" aria-hidden="true" />
        <ParticleField />
      </div>

      <div className="relative z-10 mx-auto flex h-full max-w-7xl flex-col justify-center px-6 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="max-w-xl"
        >
          <span className="inline-flex items-center gap-1.5 mb-3 text-xs uppercase tracking-[0.2em] text-[var(--color-red-accent)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-red)] shadow-[0_0_8px_rgba(229,9,20,0.9)]" />
            Featured Pick
          </span>
          <h1 className="font-[family-name:var(--font-display)] text-5xl sm:text-6xl tracking-wide leading-[1.05] mb-4">
            {movie.title.replace(/\s*\(\d{4}\)$/, "")}
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mb-2">
            {genreList(movie.genres).join(" • ")}
            {movie.year ? ` • ${movie.year}` : ""}
          </p>
          {movie.synopsis && (
            <p className="text-[var(--color-text-muted)] mb-6 line-clamp-3 leading-relaxed">{movie.synopsis}</p>
          )}
          <div className="flex items-center gap-3">
            <Link
              href={`/movie/${movie.id}`}
              className="flex items-center gap-2 rounded-full bg-[var(--color-red)] px-6 py-3 font-medium text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_28px_rgba(229,9,20,0.55)] transition-all"
            >
              <Play size={16} fill="currentColor" /> View details
            </Link>
            <Link
              href={`/movie/${movie.id}`}
              className="glass flex items-center gap-2 rounded-full px-6 py-3 font-medium hover:border-[var(--color-red)]/60 transition-colors"
            >
              <Info size={16} /> More info
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
