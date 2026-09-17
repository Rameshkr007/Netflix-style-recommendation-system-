"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { Header } from "@/components/Header";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { TasteDNA } from "@/lib/types";

const GENRE_COLORS: Record<string, string> = {
  Action: "#ff6b4a", Adventure: "#ff8a65", Animation: "#4ad6ff", Comedy: "#ffd84a",
  Crime: "#8a8a99", Documentary: "#6be38a", Drama: "#e50914", Family: "#ffb6e0",
  Fantasy: "#a875ff", Horror: "#7a0f0f", Mystery: "#5c4aff", Romance: "#ff6fa6",
  "Sci-Fi": "#3ddbd9", Thriller: "#ff3b3b", War: "#b20710", Anime: "#ff7ad9", Musical: "#f0e14a",
};

function genreColor(genre: string): string {
  return GENRE_COLORS[genre] ?? "#e50914";
}

/* The signature element: a "taste constellation" -- glowing nodes sized by
   genre share, arranged radially, replacing the generic bar-chart treatment
   a Taste-DNA feature usually gets. Distance from center is irrelevant;
   angle + node size + color encode the breakdown so it reads as a personal
   "fingerprint" rather than a report. */
function TasteConstellation({ breakdown }: { breakdown: TasteDNA["genre_breakdown"] }) {
  const entries = Object.entries(breakdown).sort((a, b) => b[1].percentage - a[1].percentage);
  const size = 360;
  const center = size / 2;
  const maxRadius = size / 2 - 50;
  const reduceMotion = useReducedMotion();

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[360px]" role="img" aria-label="Taste DNA constellation">
      {/* faint orbit rings for scale reference */}
      {[0.33, 0.66, 1].map((f) => (
        <circle
          key={f}
          cx={center}
          cy={center}
          r={maxRadius * f}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={1}
        />
      ))}

      {entries.map(([genre, data], i) => {
        const angle = (i / entries.length) * Math.PI * 2 - Math.PI / 2;
        const radius = maxRadius * (0.35 + Math.min(data.percentage, 40) / 40 * 0.6);
        const x = center + radius * Math.cos(angle);
        const y = center + radius * Math.sin(angle);
        const nodeSize = 8 + Math.sqrt(data.percentage) * 4;
        const color = genreColor(genre);

        return (
          <g key={genre}>
            <motion.line
              x1={center}
              y1={center}
              x2={x}
              y2={y}
              stroke={color}
              strokeWidth={1.5}
              initial={reduceMotion ? { opacity: 0.3 } : { pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 0.3 }}
              transition={reduceMotion ? { duration: 0 } : { duration: 0.7, delay: i * 0.06, ease: "easeOut" }}
            />
            <motion.circle
              initial={reduceMotion ? { opacity: 1 } : { r: 0, opacity: 0 }}
              animate={{ r: nodeSize, opacity: 1 }}
              transition={reduceMotion ? { duration: 0 } : { duration: 0.6, delay: i * 0.06, ease: "easeOut" }}
              cx={x}
              cy={y}
              fill={color}
              fillOpacity={0.85}
              style={{ filter: `drop-shadow(0 0 6px ${color}aa)` }}
            />
            <text
              x={x}
              y={y - nodeSize - 8}
              textAnchor="middle"
              fontSize={11}
              fill="var(--color-text-muted)"
              className="font-medium"
            >
              {genre}
            </text>
            <text x={x} y={y + nodeSize + 14} textAnchor="middle" fontSize={9} fill="var(--color-text-dim)">
              {data.percentage}%
            </text>
          </g>
        );
      })}

      <motion.circle
        cx={center}
        cy={center}
        r={5}
        fill="var(--color-red)"
        animate={
          reduceMotion
            ? {}
            : {
                filter: [
                  "drop-shadow(0 0 4px rgba(229,9,20,0.6))",
                  "drop-shadow(0 0 12px rgba(229,9,20,0.95))",
                  "drop-shadow(0 0 4px rgba(229,9,20,0.6))",
                ],
              }
        }
        style={reduceMotion ? { filter: "drop-shadow(0 0 6px rgba(229,9,20,0.75))" } : undefined}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
    </svg>
  );
}

export default function ProfilePage() {
  const { user, loading: authLoading } = useAuth();
  const [dna, setDna] = useState<TasteDNA | null>(null);
  const [dataLoading, setDataLoading] = useState(false);

  useEffect(() => {
    if (!user) return;
    setDataLoading(true);
    api
      .tasteDna()
      .then(setDna)
      .catch(() => setDna(null))
      .finally(() => setDataLoading(false));
  }, [user]);

  return (
    <div className="flex-1">
      <Header />
      <div className="mx-auto max-w-5xl px-6 sm:px-10 py-10">
        <div className="mb-8 flex items-center gap-2">
          <Sparkles size={20} className="text-[var(--color-red)]" />
          <h1 className="font-[family-name:var(--font-display)] text-2xl tracking-wide">Your Taste DNA</h1>
        </div>

        {!authLoading && !user ? (
          <p className="text-[var(--color-text-muted)]">
            <Link href="/login" className="text-[var(--color-red-accent)] hover:text-white">
              Sign in
            </Link>{" "}
            to see your taste profile.
          </p>
        ) : authLoading || dataLoading ? (
          <div className="skeleton h-[360px] w-full max-w-[360px] rounded-full mx-auto" />
        ) : !dna || dna.total_rated === 0 ? (
          <p className="text-[var(--color-text-muted)]">
            Rate a few titles and your Taste DNA will take shape here.
          </p>
        ) : (
          <div className="grid gap-10 sm:grid-cols-2 items-center">
            <div className="flex justify-center">
              <TasteConstellation breakdown={dna.genre_breakdown} />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[var(--color-red-accent)] mb-1">
                Viewing Personality
              </p>
              <p className="font-[family-name:var(--font-display)] text-3xl tracking-wide mb-4">
                {dna.viewing_personality}
              </p>
              <p className="text-sm text-[var(--color-text-muted)] mb-6">
                Based on {dna.total_rated} rated title{dna.total_rated === 1 ? "" : "s"}.
              </p>
              <div className="space-y-2.5">
                {Object.entries(dna.genre_breakdown)
                  .sort((a, b) => b[1].percentage - a[1].percentage)
                  .map(([genre, data]) => (
                    <div key={genre} className="flex items-center gap-3">
                      <span
                        className="h-2.5 w-2.5 rounded-full shrink-0"
                        style={{ background: genreColor(genre) }}
                      />
                      <span className="text-sm w-24 shrink-0">{genre}</span>
                      <div className="h-1.5 flex-1 rounded-full bg-[var(--color-surface)] overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${data.percentage}%`, background: genreColor(genre) }}
                        />
                      </div>
                      <span className="text-xs text-[var(--color-text-dim)] w-10 text-right">
                        {data.percentage}%
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
