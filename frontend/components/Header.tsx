"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Search, Sparkles, Bookmark, LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function Header() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [scrolled, setScrolled] = useState(false);
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  }

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled ? "glass-strong border-b border-[var(--color-red)]/15" : "bg-gradient-to-b from-black/70 to-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <span className="font-[family-name:var(--font-display)] text-2xl tracking-wide text-gradient-red">
            APERTURE
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-5 text-sm text-[var(--color-text-muted)]">
          <Link href="/" className="hover:text-[var(--color-text)] transition-colors">
            Home
          </Link>
          <Link href="/search" className="hover:text-[var(--color-text)] transition-colors">
            Browse
          </Link>
          {user && (
            <Link href="/watchlist" className="hover:text-[var(--color-text)] transition-colors">
              My List
            </Link>
          )}
        </nav>

        <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md ml-auto">
          <div className="glass flex items-center gap-2 rounded-full px-4 py-2 transition-colors focus-within:border-[var(--color-red)]/60">
            <Search size={16} className="text-[var(--color-text-dim)] shrink-0" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search titles, actors, directors…"
              className="w-full bg-transparent text-sm outline-none placeholder:text-[var(--color-text-dim)]"
            />
          </div>
        </form>

        {user ? (
          <div className="relative shrink-0">
            <button
              onClick={() => setMenuOpen((v) => !v)}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-red)]/20 text-[var(--color-red-accent)] font-semibold border border-[var(--color-border-strong)] hover:border-[var(--color-red)]/50 transition-colors"
              aria-label="Account menu"
            >
              {user.display_name.charAt(0).toUpperCase()}
            </button>
            {menuOpen && (
              <div className="glass-strong absolute right-0 mt-2 w-52 overflow-hidden rounded-xl text-sm">
                <div className="px-4 py-3 border-b border-[var(--color-border)]">
                  <p className="font-medium truncate">{user.display_name}</p>
                  <p className="text-xs text-[var(--color-text-dim)] truncate">{user.email}</p>
                </div>
                <Link
                  href="/profile"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2 px-4 py-2.5 hover:bg-[var(--color-surface-hover)] transition-colors"
                >
                  <Sparkles size={15} /> Taste DNA
                </Link>
                <Link
                  href="/watchlist"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2 px-4 py-2.5 hover:bg-[var(--color-surface-hover)] transition-colors"
                >
                  <Bookmark size={15} /> My List
                </Link>
                <button
                  onClick={() => {
                    logout();
                    setMenuOpen(false);
                    router.push("/");
                  }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-[var(--color-surface-hover)] transition-colors text-[var(--color-red-accent)]"
                >
                  <LogOut size={15} /> Sign out
                </button>
              </div>
            )}
          </div>
        ) : (
          <Link
            href="/login"
            className="shrink-0 flex items-center gap-2 rounded-full bg-[var(--color-red)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--color-red-hover)] hover:shadow-[0_0_20px_rgba(229,9,20,0.5)] transition-all"
          >
            <UserIcon size={15} /> Sign in
          </Link>
        )}
      </div>
    </header>
  );
}
