"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { HeroBanner } from "@/components/HeroBanner";
import { MovieRail } from "@/components/MovieRail";
import { MoodPicker } from "@/components/MoodPicker";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { Movie, RecommendationItem } from "@/lib/types";

export default function Home() {
  const { user } = useAuth();

  const [trending, setTrending] = useState<Movie[]>([]);
  const [forMe, setForMe] = useState<RecommendationItem[]>([]);
  const [actionPicks, setActionPicks] = useState<Movie[]>([]);
  const [scifiPicks, setScifiPicks] = useState<Movie[]>([]);
  const [hollywoodPicks, setHollywoodPicks] = useState<Movie[]>([]);
  const [bollywoodPicks, setBollywoodPicks] = useState<Movie[]>([]);
  const [tollywoodPicks, setTollywoodPicks] = useState<Movie[]>([]);
  const [moodResults, setMoodResults] = useState<Movie[] | null>(null);
  const [moodLabel, setMoodLabel] = useState("");
  const [watchlistIds, setWatchlistIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const trendingPromise = api.trending(20).catch(() => []);
      const actionPromise = api.listMovies({ genre: "Action", limit: 16 }).catch(() => []);
      const scifiPromise = api.listMovies({ genre: "Sci-Fi", limit: 16 }).catch(() => []);
      const hollywoodPromise = api.listMovies({ region: "Hollywood", limit: 20 }).catch(() => []);
      const bollywoodPromise = api.listMovies({ region: "Bollywood", limit: 20 }).catch(() => []);
      const tollywoodPromise = api.listMovies({ region: "Tollywood", limit: 20 }).catch(() => []);
      const forMePromise = user ? api.forMe(16).catch(() => []) : Promise.resolve([]);
      const watchlistPromise = user ? api.myWatchlist().catch(() => []) : Promise.resolve([]);

      const [trendingRes, actionRes, scifiRes, hollywoodRes, bollywoodRes, tollywoodRes, forMeRes, watchlistRes] = await Promise.all([
        trendingPromise,
        actionPromise,
        scifiPromise,
        hollywoodPromise,
        bollywoodPromise,
        tollywoodPromise,
        forMePromise,
        watchlistPromise,
      ]);

      if (cancelled) return;
      setTrending(trendingRes);
      setActionPicks(actionRes);
      setScifiPicks(scifiRes);
      setHollywoodPicks(hollywoodRes);
      setBollywoodPicks(bollywoodRes);
      setTollywoodPicks(tollywoodRes);
      setForMe(forMeRes);
      setWatchlistIds(new Set(watchlistRes.map((m) => m.id)));
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [user]);

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
      // a toast/error-banner system would surface this in a fuller build
    }
  }

  const heroMovie = trending[0] ?? forMe[0]?.movie;

  return (
    <div className="flex-1">
      <Header />

      {heroMovie && <HeroBanner movie={heroMovie} />}

      <div className="relative z-10 -mt-16 sm:-mt-24 space-y-2 pb-16">
        <MoodPicker
          onResults={(movies, mood) => {
            setMoodResults(movies);
            setMoodLabel(mood);
          }}
        />

        {moodResults && (
          <MovieRail
            title={`Picks for "${moodLabel}"`}
            subtitle="AI mood match, based on the genres that fit how you're feeling"
            movies={moodResults}
            onAddToWatchlist={user ? handleAddToWatchlist : undefined}
            watchlistIds={watchlistIds}
          />
        )}

        {user && (
          <MovieRail
            title="Recommended for you"
            subtitle="Hybrid picks: people with similar taste + titles like what you've rated"
            recommendations={forMe}
            loading={loading}
            onAddToWatchlist={handleAddToWatchlist}
            watchlistIds={watchlistIds}
          />
        )}

        <MovieRail
          title="Trending Now"
          subtitle="What's getting watched across Aperture right now"
          movies={trending}
          loading={loading}
          onAddToWatchlist={user ? handleAddToWatchlist : undefined}
          watchlistIds={watchlistIds}
        />

        <MovieRail
          title="Action & Adventure"
          movies={actionPicks}
          loading={loading}
          onAddToWatchlist={user ? handleAddToWatchlist : undefined}
          watchlistIds={watchlistIds}
        />

        <MovieRail
          title="Sci-Fi Worlds"
          movies={scifiPicks}
          loading={loading}
          onAddToWatchlist={user ? handleAddToWatchlist : undefined}
          watchlistIds={watchlistIds}
        />

        <MovieRail
          title="Hollywood Spotlight"
          subtitle="Big-screen stories from Hollywood"
          movies={hollywoodPicks}
          loading={loading}
          onAddToWatchlist={user ? handleAddToWatchlist : undefined}
          watchlistIds={watchlistIds}
        />

        <MovieRail
          title="Bollywood Stories"
          subtitle="Romance, drama and spectacle from Bollywood"
          movies={bollywoodPicks}
          loading={loading}
          onAddToWatchlist={user ? handleAddToWatchlist : undefined}
          watchlistIds={watchlistIds}
        />

        <MovieRail
          title="Tollywood Hits"
          subtitle="Action-packed stories from Tollywood"
          movies={tollywoodPicks}
          loading={loading}
          onAddToWatchlist={user ? handleAddToWatchlist : undefined}
          watchlistIds={watchlistIds}
        />
      </div>
    </div>
  );
}
