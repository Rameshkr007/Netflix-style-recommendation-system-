"""
Generates a realistic, MovieLens-shaped synthetic dataset (movies.csv, ratings.csv,
tags.csv) for local development and CI testing, so the ML pipeline and API can run
end-to-end without needing network access to download the real dataset first.

This is NOT a replacement for real MovieLens data -- it exists so:
  1. `docker compose up` works out of the box with zero manual steps
  2. unit tests / CI runs are deterministic and fast
  3. you can swap in real ml-latest-small data later via download_movielens.py
     and nothing else needs to change (same column schema).

Run:
    python scripts/generate_sample_data.py
"""
import os
import random

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
    "Drama", "Family", "Fantasy", "Horror", "Mystery", "Romance",
    "Sci-Fi", "Thriller", "War", "Anime", "Musical",
]

TITLE_WORDS_A = [
    "Shadow", "Silent", "Last", "Eternal", "Hidden", "Broken", "Crimson",
    "Midnight", "Iron", "Lost", "Forgotten", "Rising", "Distant", "Sacred",
    "Frozen", "Burning", "Quiet", "Endless", "Golden", "Dark",
]
TITLE_WORDS_B = [
    "Horizon", "Kingdom", "City", "Empire", "Garden", "Storm", "Legacy",
    "Voyage", "Protocol", "Symphony", "Rebellion", "Frontier", "Dynasty",
    "Echo", "Paradox", "Sanctuary", "Inferno", "Odyssey", "Republic", "Code",
]

DIRECTORS = [
    "A. Tarkov", "M. Sorrento", "L. Okafor", "J. Whitfield", "S. Yamada",
    "R. Castellano", "P. Novak", "T. Adeyemi", "K. Lindqvist", "D. Mercer",
    "H. Park", "C. Beaumont", "N. Osei", "F. Bianchi", "E. Lindgren",
]

HOLLYWOOD_DIRECTORS = [
    "C. Nolan", "A. Villeneuve", "M. Cameron", "D. Fincher", "S. Spielberg",
    "N. Burton", "G. Del Toro", "W. Anderson", "J. Nolan", "P. Jackson",
]
BOLLYWOOD_DIRECTORS = [
    "R. Kapoor", "A. Khan", "Y. Chopra", "K. Johar", "S. Bhatt",
    "M. Hirani", "R. Shetty", "V. Anand", "Z. Ansari", "S. Ali",
]
TOLLYWOOD_DIRECTORS = [
    "R. Reddy", "S. Kumar", "V. Vamsi", "N. Teja", "S. Rajamouli",
    "T. Nag", "C. Tirumala", "B. Krishna", "P. Raghav", "A. Srinivas",
]

ACTORS = [
    "Maya Linden", "Jonah Pierce", "Priya Anand", "Elias Foster", "Nina Kowalski",
    "Daniel Cho", "Sofia Bellucci", "Marcus Webb", "Ava Solano", "Theo Nakamura",
    "Layla Hassan", "Owen Brandt", "Zara Mensah", "Lucas Reiner", "Ines Duarte",
    "Sam Whitaker", "Rosa Delgado", "Felix Marchetti", "Kira Solberg", "Tobias Kane",
]

HOLLYWOOD_ACTORS = [
    "Tom Hanks", "Margot Robbie", "Leonardo DiCaprio", "Brad Pitt", "Emma Stone",
    "Ryan Gosling", "Zendaya", "Chris Evans", "Ana de Armas", "Timothée Chalamet",
]
BOLLYWOOD_ACTORS = [
    "Shah Rukh Khan", "Deepika Padukone", "Ranveer Singh", "Priyanka Chopra",
    "Amitabh Bachchan", "Alia Bhatt", "Ajay Devgn", "Kareena Kapoor", "Ranbir Kapoor", "Shraddha Kapoor",
]
TOLLYWOOD_ACTORS = [
    "Mahesh Babu", "N. T. Rama Rao", "Prabhas", "Samantha Ruth Prabhu",
    "Allu Arjun", "Ram Charan", "Pooja Hegde", "Naga Chaitanya", "Anushka Shetty", "Nayanthara",
]

REGIONAL_TITLE_PREFIXES = {
    "Hollywood": [
        "Midnight", "Silver", "Crimson", "Iron", "Neon", "Ghost", "Storm", "Velvet",
        "Royal", "Last", "Hidden", "Nightfall", "Golden", "Final", "Black"
    ],
    "Bollywood": [
        "Saffron", "Monsoon", "Dream", "Royal", "Eternal", "Heart", "Jungle", "Lagaan",
        "Lighthouse", "Love", "Dhoom", "Nawab", "Raaj", "Pardesi", "Aashiq"
    ],
    "Tollywood": [
        "Telugu", "Vijay", "Raja", "Power", "Legend", "River", "Sunrise", "Storm",
        "Royal", "Crown", "Hero", "Galaxy", "Diamond", "Dream", "Victory"
    ],
}

REGIONAL_TITLE_SUFFIXES = {
    "Hollywood": ["Sky", "Echo", "Run", "Heist", "City", "Frontier", "Signal", "Rise", "Alliance", "Kingdom"],
    "Bollywood": ["Love", "Rang", "Milan", "Dil", "Ghar", "Katha", "Nasha", "Sangam", "Azaadi", "Dhoop"],
    "Tollywood": ["Raja", "Stars", "Velugu", "Empire", "Nayak", "Rangula", "Vikram", "Sena", "Waves", "Sundari"],
}


def make_movies(n=400, regional_n=500):
    rows = []
    for movie_id in range(1, n + 1):
        n_genres = random.randint(1, 3)
        genres = random.sample(GENRES, n_genres)
        title = f"{random.choice(TITLE_WORDS_A)} {random.choice(TITLE_WORDS_B)}"
        year = random.randint(1990, 2026)
        director = random.choice(DIRECTORS)
        cast = random.sample(ACTORS, 3)
        content_type = random.choices(
            ["movie", "tv_show", "anime", "documentary"],
            weights=[0.55, 0.25, 0.12, 0.08],
        )[0]
        rows.append({
            "movieId": movie_id,
            "title": f"{title} ({year})",
            "genres": "|".join(genres),
            "year": year,
            "director": director,
            "cast": ", ".join(cast),
            "content_type": content_type,
            "runtime_minutes": random.randint(20, 180),
            "poster_url": f"https://picsum.photos/seed/movie{movie_id}/300/450",
            "synopsis": (
                f"A {genres[0].lower()} story set against a backdrop of "
                f"{random.choice(['war', 'love', 'betrayal', 'discovery', 'survival', 'ambition'])}, "
                f"directed by {director}."
            ),
        })

    for movie_id in range(n + 1, n + regional_n + 1):
        region = random.choice(["Hollywood", "Bollywood", "Tollywood"])
        title = f"{random.choice(REGIONAL_TITLE_PREFIXES[region])} {random.choice(REGIONAL_TITLE_SUFFIXES[region])}"
        year = random.randint(2008, 2026)
        director_pool = {
            "Hollywood": HOLLYWOOD_DIRECTORS,
            "Bollywood": BOLLYWOOD_DIRECTORS,
            "Tollywood": TOLLYWOOD_DIRECTORS,
        }[region]
        actor_pool = {
            "Hollywood": HOLLYWOOD_ACTORS,
            "Bollywood": BOLLYWOOD_ACTORS,
            "Tollywood": TOLLYWOOD_ACTORS,
        }[region]
        director = random.choice(director_pool)
        cast = random.sample(actor_pool, 3)
        genres = random.sample(["Action", "Drama", "Romance", "Comedy", "Thriller", "Adventure", "Mystery", "Sci-Fi"], k=random.randint(2, 3))
        content_type = random.choices(["movie", "tv_show", "movie", "movie"], weights=[0.15, 0.1, 0.6, 0.15])[0]
        rows.append({
            "movieId": movie_id,
            "title": f"{title} ({year})",
            "genres": "|".join(genres),
            "year": year,
            "director": director,
            "cast": ", ".join(cast),
            "content_type": content_type,
            "runtime_minutes": random.randint(90, 190),
            "poster_url": f"https://picsum.photos/seed/movie{movie_id}/300/450",
            "synopsis": (
                f"A {region.lower()} cinematic story of {random.choice(['love', 'revenge', 'courage', 'ambition', 'family', 'redemption'])}, "
                f"featuring a powerful ensemble cast and directed by {director}."
            ),
        })
    return pd.DataFrame(rows)


def make_ratings(movies_df, n_users=250, avg_ratings_per_user=40):
    rows = []
    movie_ids = movies_df["movieId"].tolist()

    # give each movie a latent "quality" and each user a latent "generosity"
    # so ratings aren't pure noise -- this lets CF actually learn signal
    movie_quality = {mid: np.random.normal(3.4, 0.6) for mid in movie_ids}

    for user_id in range(1, n_users + 1):
        user_bias = np.random.normal(0, 0.4)
        # users have genre preferences -> content-based signal exists too
        liked_genres = set(random.sample(GENRES, random.randint(2, 4)))
        n_ratings = max(5, int(np.random.normal(avg_ratings_per_user, 15)))
        rated_movies = random.sample(movie_ids, min(n_ratings, len(movie_ids)))

        for mid in rated_movies:
            movie_genres = set(
                movies_df.loc[movies_df.movieId == mid, "genres"].values[0].split("|")
            )
            genre_match_bonus = 0.6 if liked_genres & movie_genres else -0.3
            score = movie_quality[mid] + user_bias + genre_match_bonus
            score += np.random.normal(0, 0.5)
            rating = round(min(5.0, max(0.5, score)) * 2) / 2  # nearest 0.5
            timestamp = random.randint(1_500_000_000, 1_770_000_000)
            rows.append({
                "userId": user_id,
                "movieId": mid,
                "rating": rating,
                "timestamp": timestamp,
            })
    return pd.DataFrame(rows)


def make_tags(movies_df, ratings_df, n_tags=600):
    sample_tags = [
        "mind-bending", "slow burn", "tearjerker", "feel-good", "binge-worthy",
        "underrated", "visually stunning", "great soundtrack", "plot twist",
        "based on true events", "cult classic", "edge-of-seat", "thought-provoking",
        "rewatchable", "dark", "wholesome", "stylish", "atmospheric",
    ]
    user_movie_pairs = ratings_df[["userId", "movieId"]].drop_duplicates()
    chosen = user_movie_pairs.sample(min(n_tags, len(user_movie_pairs)), random_state=42)
    rows = []
    for _, row in chosen.iterrows():
        rows.append({
            "userId": row.userId,
            "movieId": row.movieId,
            "tag": random.choice(sample_tags),
            "timestamp": random.randint(1_500_000_000, 1_770_000_000),
        })
    return pd.DataFrame(rows)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    movies_df = make_movies(n=400, regional_n=500)
    ratings_df = make_ratings(movies_df, n_users=250)
    tags_df = make_tags(movies_df, ratings_df)

    movies_df.to_csv(os.path.join(DATA_DIR, "movies.csv"), index=False)
    ratings_df.to_csv(os.path.join(DATA_DIR, "ratings.csv"), index=False)
    tags_df.to_csv(os.path.join(DATA_DIR, "tags.csv"), index=False)

    print(f"movies.csv  -> {len(movies_df)} titles")
    print(f"ratings.csv -> {len(ratings_df)} ratings from {ratings_df.userId.nunique()} users")
    print(f"tags.csv    -> {len(tags_df)} tags")
    print(f"Written to {os.path.abspath(DATA_DIR)}")


if __name__ == "__main__":
    main()
