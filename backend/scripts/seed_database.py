"""
Seeds the database from backend/data/{movies,ratings}.csv and creates two
convenience accounts for local testing:

    admin@example.com    / Admin1234!   (role=admin)
    demo@example.com     / Demo1234!    (role=user, with seeded ratings)

Run after the containers are up:
    docker compose exec api python scripts/seed_database.py
or locally:
    python scripts/seed_database.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.db_models import ContentType, Movie, Rating, User, UserRole  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if db.query(Movie).count() > 0:
            print("Database already has movies -- skipping catalog seed (delete rows to reseed).")
        else:
            movies_path = os.path.join(DATA_DIR, "movies.csv")
            if not os.path.exists(movies_path):
                print(f"No movies.csv found at {movies_path}. Run generate_sample_data.py or download_movielens.py first.")
                return

            movies_df = pd.read_csv(movies_path)
            print(f"Seeding {len(movies_df)} titles ...")
            id_map = {}
            for _, row in movies_df.iterrows():
                content_type = row.get("content_type", "movie")
                try:
                    ct_enum = ContentType(content_type)
                except ValueError:
                    ct_enum = ContentType.MOVIE
                movie = Movie(
                    title=row["title"],
                    genres=row["genres"],
                    year=int(row["year"]) if not pd.isna(row.get("year")) else None,
                    director=row.get("director"),
                    cast=row.get("cast"),
                    content_type=ct_enum,
                    runtime_minutes=int(row["runtime_minutes"]) if not pd.isna(row.get("runtime_minutes")) else None,
                    poster_url=row.get("poster_url"),
                    synopsis=row.get("synopsis"),
                )
                db.add(movie)
                db.flush()  # get movie.id without a full commit
                id_map[int(row["movieId"])] = movie.id
            db.commit()
            print("Movies seeded.")

            ratings_path = os.path.join(DATA_DIR, "ratings.csv")
            if os.path.exists(ratings_path):
                ratings_df = pd.read_csv(ratings_path)
                print(f"Seeding {len(ratings_df)} ratings (this drives the demo recommendations) ...")

                # The CSV's userId values are synthetic; create lightweight
                # placeholder User rows for them so Rating's FK is satisfiable
                # and the collaborative model has real interaction data.
                csv_user_ids = sorted(ratings_df["userId"].unique())
                user_id_map = {}
                for csv_uid in csv_user_ids:
                    placeholder = User(
                        email=f"seed_user_{csv_uid}@placeholder.local",
                        hashed_password=None,
                        display_name=f"Seed User {csv_uid}",
                        role=UserRole.USER,
                    )
                    db.add(placeholder)
                    db.flush()
                    user_id_map[csv_uid] = placeholder.id
                db.commit()

                for _, row in ratings_df.iterrows():
                    movie_db_id = id_map.get(int(row["movieId"]))
                    user_db_id = user_id_map.get(int(row["userId"]))
                    if movie_db_id is None or user_db_id is None:
                        continue
                    db.add(Rating(user_id=user_db_id, movie_id=movie_db_id, rating=float(row["rating"])))
                db.commit()
                print("Ratings seeded.")

        if not db.query(User).filter(User.email == "admin@example.com").first():
            db.add(User(
                email="admin@example.com",
                hashed_password=hash_password("Admin1234!"),
                display_name="Admin",
                role=UserRole.ADMIN,
            ))
            print("Created admin@example.com / Admin1234!")

        if not db.query(User).filter(User.email == "demo@example.com").first():
            db.add(User(
                email="demo@example.com",
                hashed_password=hash_password("Demo1234!"),
                display_name="Demo User",
                role=UserRole.USER,
                favorite_genres="Sci-Fi,Action,Drama",
            ))
            print("Created demo@example.com / Demo1234!")

        db.commit()
        print("Seeding complete.")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
