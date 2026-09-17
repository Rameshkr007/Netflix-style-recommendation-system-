"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { LogIn } from "lucide-react";
import { useAuth, ApiError } from "@/lib/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
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
        className="glass-strong w-full max-w-sm rounded-2xl p-8"
      >
        <Link href="/" className="font-[family-name:var(--font-display)] text-2xl text-gradient-red">
          APERTURE
        </Link>
        <h1 className="mt-6 text-xl font-semibold">Welcome back</h1>
        <p className="mt-1 text-sm text-[var(--color-text-muted)]">Sign in to pick up where you left off.</p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="glass w-full rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-[var(--color-red)]"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          {error && <p className="text-sm text-[var(--color-red-accent)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--color-red)] py-2.5 text-sm font-medium text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_20px_rgba(229,9,20,0.45)] transition-all disabled:opacity-50"
          >
            <LogIn size={15} /> {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
          New here?{" "}
          <Link href="/register" className="text-[var(--color-red-accent)] hover:text-white">
            Create an account
          </Link>
        </p>

        <p className="mt-4 text-center text-xs text-[var(--color-text-dim)]">
          Demo account: demo@example.com / Demo1234!
        </p>
      </motion.div>
    </div>
  );
}
