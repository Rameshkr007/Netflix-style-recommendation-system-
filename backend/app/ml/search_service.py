"""
Advanced Search Service
--------------------------
Combines:
  - Fuzzy substring/typo-tolerant matching on titles (difflib, stdlib-only)
  - Semantic search via the same TF-IDF content vectors used by the
    content-based recommender (so "space war movie" can match a sci-fi
    title even if the word "space" never appears in its title)
  - Structured filters: genre / actor / director / content type

This satisfies "Semantic Search", "Fuzzy Search", "Genre/Actor/Director
Search" from the spec in one unified `SearchService.search()` call.
Voice search is a frontend concern (Web Speech API) that transcribes
audio to text and calls this same endpoint -- no separate backend logic
needed.
"""
from __future__ import annotations

import difflib

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SearchService:
    def __init__(self, movies_df: pd.DataFrame):
        self.movies_df = movies_df.reset_index(drop=True)
        soup = (
            self.movies_df["genres"].str.replace("|", " ", regex=False).fillna("")
            + " "
            + self.movies_df["director"].fillna("")
            + " "
            + self.movies_df["cast"].fillna("")
            + " "
            + self.movies_df["synopsis"].fillna("")
            + " "
            + self.movies_df["title"].fillna("")
        ).str.lower()
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(soup)

    def fuzzy_title_match(self, query: str, limit: int = 5, cutoff: float = 0.4) -> list[int]:
        titles = self.movies_df["title"].tolist()
        close = difflib.get_close_matches(query, titles, n=limit, cutoff=cutoff)
        return self.movies_df[self.movies_df["title"].isin(close)]["movieId"].tolist()

    def semantic_search(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        query_vec = self._vectorizer.transform([query.lower()])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        ranked_idx = sims.argsort()[::-1][:top_k]
        return [
            (int(self.movies_df.iloc[i]["movieId"]), float(sims[i]))
            for i in ranked_idx
            if sims[i] > 0
        ]

    def search(
        self,
        query: str,
        genre: str | None = None,
        actor: str | None = None,
        director: str | None = None,
        content_type: str | None = None,
        top_k: int = 20,
    ) -> list[int]:
        """Unified entry point: blends fuzzy title hits + semantic hits, then applies structured filters."""
        candidates: dict[int, float] = {}

        for mid in self.fuzzy_title_match(query, limit=top_k):
            candidates[mid] = candidates.get(mid, 0.0) + 1.0  # exact-ish title match wins

        for mid, score in self.semantic_search(query, top_k=top_k * 2):
            candidates[mid] = candidates.get(mid, 0.0) + score

        if not candidates:
            return []

        df = self.movies_df[self.movies_df["movieId"].isin(candidates.keys())].copy()

        if genre:
            df = df[df["genres"].str.contains(genre, case=False, na=False)]
        if actor:
            df = df[df["cast"].str.contains(actor, case=False, na=False)]
        if director:
            df = df[df["director"].str.contains(director, case=False, na=False)]
        if content_type:
            df = df[df["content_type"].str.lower() == content_type.lower()] if "content_type" in df.columns else df

        df["_score"] = df["movieId"].map(candidates)
        df = df.sort_values("_score", ascending=False)
        return df["movieId"].head(top_k).tolist()

    def suggestions(self, partial_query: str, limit: int = 6) -> list[str]:
        """Lightweight autocomplete: titles whose text starts with or contains the partial query."""
        if not partial_query:
            return []
        lower_q = partial_query.lower()
        titles = self.movies_df["title"].tolist()
        starts_with = [t for t in titles if t.lower().startswith(lower_q)]
        contains = [t for t in titles if lower_q in t.lower() and t not in starts_with]
        return (starts_with + contains)[:limit]
