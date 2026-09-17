"""
Mood-Based Recommendation Engine
-----------------------------------
Takes free-text mood input ("I'm feeling heartbroken tonight") and maps it
to a weighted set of genres, then recommends top-rated content in those
genres. Uses a keyword-overlap + TF-IDF similarity approach against a small
curated mood-lexicon -- this avoids requiring a large external NLP model
just to classify mood into ~8 buckets, while still handling phrasing
variation reasonably well (e.g. "heartbroken" -> sad/romantic).

For a production system with heavier traffic, swap MOOD_LEXICON matching
for a call to a hosted sentence-embedding model (e.g. via the Anthropic or
OpenAI embeddings API) and do nearest-neighbor lookup against the same
mood->genre map; the interface (`MoodRecommender.recommend`) stays the same.
"""
from __future__ import annotations

import re

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MOOD_LEXICON: dict[str, list[str]] = {
    "happy": ["happy", "joyful", "cheerful", "great mood", "good mood", "upbeat", "fun"],
    "sad": ["sad", "down", "heartbroken", "depressed", "crying", "blue", "lonely", "grief"],
    "excited": ["excited", "pumped", "hyped", "thrilled", "adrenaline", "energetic"],
    "motivated": ["motivated", "inspired", "determined", "ambitious", "productive", "focus"],
    "romantic": ["romantic", "love", "date night", "crush", "valentine", "heartwarming"],
    "scared": ["scared", "spooky", "halloween", "creepy", "horror mood", "thrill"],
    "relaxed": ["relaxed", "chill", "calm", "cozy", "lazy", "unwind", "sunday"],
    "nostalgic": ["nostalgic", "throwback", "childhood", "old school", "retro"],
}

MOOD_TO_GENRES: dict[str, list[str]] = {
    "happy": ["Comedy", "Family", "Animation", "Musical"],
    "sad": ["Drama", "Romance"],
    "excited": ["Action", "Adventure", "Thriller", "Sci-Fi"],
    "motivated": ["Documentary", "Drama", "Sci-Fi"],
    "romantic": ["Romance", "Drama"],
    "scared": ["Horror", "Thriller", "Mystery"],
    "relaxed": ["Comedy", "Family", "Animation"],
    "nostalgic": ["Animation", "Family", "Musical"],
}


class MoodRecommender:
    def __init__(self, movies_df: pd.DataFrame, ratings_df: pd.DataFrame | None = None):
        self.movies_df = movies_df
        self.ratings_df = ratings_df
        self._mood_keys = list(MOOD_LEXICON.keys())
        corpus = [" ".join(MOOD_LEXICON[m]) for m in self._mood_keys]
        self._vectorizer = TfidfVectorizer()
        self._mood_matrix = self._vectorizer.fit_transform(corpus)

    def detect_mood(self, text: str) -> tuple[str, float]:
        """Returns (mood_label, confidence_score)."""
        cleaned = re.sub(r"[^a-z\s]", " ", text.lower())

        # fast path: direct keyword hit
        for mood, keywords in MOOD_LEXICON.items():
            if any(kw in cleaned for kw in keywords):
                return mood, 1.0

        # fallback: TF-IDF similarity against the mood lexicon corpus
        query_vec = self._vectorizer.transform([cleaned])
        sims = cosine_similarity(query_vec, self._mood_matrix)[0]
        best_idx = sims.argmax()
        if sims[best_idx] == 0:
            return "relaxed", 0.0  # neutral default
        return self._mood_keys[best_idx], float(sims[best_idx])

    def recommend(self, mood_text: str, top_k: int = 12) -> dict:
        mood, confidence = self.detect_mood(mood_text)
        target_genres = set(MOOD_TO_GENRES.get(mood, []))

        def genre_match_count(genres_str: str) -> int:
            return len(set(genres_str.split("|")) & target_genres)

        scored = self.movies_df.copy()
        scored["match_score"] = scored["genres"].apply(genre_match_count)
        scored = scored[scored["match_score"] > 0].sort_values("match_score", ascending=False)

        movie_ids = scored["movieId"].head(top_k).tolist()
        return {
            "detected_mood": mood,
            "confidence": round(confidence, 3),
            "matched_genres": sorted(target_genres),
            "movie_ids": movie_ids,
        }
