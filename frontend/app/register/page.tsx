"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { UserPlus } from "lucide-react";
import { useAuth, ApiError } from "@/lib/auth-context";

const GENRES = [
  "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
  "Drama", "Family", "Fantasy", "Horror", "Mystery", "Romance",
  "Sci-Fi", "Thriller", "War", "Anime", "Musical",
];

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [genres, setGenres] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function toggleGenre(genre: string) {
    setGenres((prev) => (prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, displayName, genres);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="glass-strong w-full max-w-md rounded-2xl p-8"
      >
        <Link href="/" className="font-[family-name:var(--font-display)] text-2xl text-gradient-red">
          APERTURE
        </Link>
        <h1 className="mt-6 text-xl font-semibold">Create your account</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">
          Tell us a little about your taste so day-one recommendations aren&apos;t just guesswork.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="displayName" className="mb-1.5 block text-xs text-[var(--color-text-muted)]">
              Display name
            </label>
            <input
              id="displayName"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="glass w-full rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-[var(--color-red)]"
              placeholder="Alex"
              autoComplete="name"
            />
          </div>
          <div>
            <label htmlFor="email" className="mb-1.5 block text-xs text-[var(--color-text-muted)]">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="glass w-full rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-[var(--color-red)]"
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1.5 block text-xs text-[var(--color-text-muted)]">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="glass w-full rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-[var(--color-red)]"
              placeholder="At least 8 characters"
              autoComplete="new-password"
            />
          </div>

          <div>
            <p className="mb-2 text-xs text-[var(--color-text-muted)]">
              Favorite genres <span className="text-[var(--color-text-dim)]">(optional, pick a few)</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {GENRES.map((genre) => {
                const active = genres.includes(genre);
                return (
                  <button
                    type="button"
                    key={genre}
                    onClick={() => toggleGenre(genre)}
                    className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                      active
                        ? "border-[var(--color-red)] bg-[var(--color-red)]/15 text-[var(--color-red-accent)]"
                        : "border-[var(--color-border-strong)] text-[var(--color-text-muted)] hover:border-[var(--color-red)]"
                    }`}
                  >
                    {genre}
                  </button>
                );
              })}
            </div>
          </div>

          {error && <p className="text-sm text-[var(--color-red-accent)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--color-red)] py-2.5 text-sm font-medium text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_20px_rgba(229,9,20,0.45)] transition-all disabled:opacity-50"
          >
            <UserPlus size={15} /> {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
          Already have an account?{" "}
          <Link href="/login" className="text-[var(--color-red-accent)] hover:text-white">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
