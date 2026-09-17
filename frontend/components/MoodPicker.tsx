"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Movie } from "@/lib/types";

const QUICK_MOODS = ["Happy", "Sad", "Excited", "Motivated", "Romantic", "Scared", "Relaxed"];

export function MoodPicker({ onResults }: { onResults: (movies: Movie[], mood: string) => void }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitMood(moodText: string) {
    if (!moodText.trim() || loading) return;
    setLoading(true);
    try {
      const movies = await api.moodRecommend(moodText);
      onResults(movies, moodText);
    } catch {
      onResults([], moodText);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="px-6 sm:px-10 py-6">
      <div className="glass-strong rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={18} className="text-[var(--color-red-accent)]" />
          <h2 className="font-[family-name:var(--font-display)] text-lg tracking-wide">
            What&apos;s your mood tonight?
          </h2>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitMood(text);
          }}
          className="flex gap-2 mb-3"
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Tell me how you're feeling… e.g. 'wiped out but want something fun'"
            className="glass flex-1 rounded-full px-4 py-2.5 text-sm outline-none placeholder:text-[var(--color-text-dim)] focus:border-[var(--color-red)]"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-full bg-[var(--color-red)] px-5 py-2.5 text-sm font-medium text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_18px_rgba(229,9,20,0.5)] transition-all disabled:opacity-50"
          >
            <AnimatePresence mode="wait">
              {loading ? (
                <motion.span key="loading" className="flex items-center gap-1.5">
                  <Loader2 size={14} className="animate-spin" /> Reading the room…
                </motion.span>
              ) : (
                <motion.span key="idle">Find picks</motion.span>
              )}
            </AnimatePresence>
          </button>
        </form>
        <div className="flex flex-wrap gap-2">
          {QUICK_MOODS.map((mood) => (
            <button
              key={mood}
              onClick={() => {
                setText(mood);
                submitMood(mood);
              }}
              className="rounded-full border border-[var(--color-border-strong)] px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:border-[var(--color-red)] hover:text-[var(--color-text)] transition-colors"
            >
              {mood}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
