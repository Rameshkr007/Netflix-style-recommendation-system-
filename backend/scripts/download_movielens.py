"""
Downloads the MovieLens ml-latest-small dataset (~1MB, 100k ratings, 9k movies)
from GroupLens and unpacks it into backend/data/.

Run this once before training:
    python scripts/download_movielens.py
"""
import urllib.request
import zipfile
import io
import os

URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Downloading MovieLens dataset from {URL} ...")
    with urllib.request.urlopen(URL) as resp:
        buf = io.BytesIO(resp.read())

    print("Extracting ...")
    with zipfile.ZipFile(buf) as zf:
        zf.extractall(DATA_DIR)

    extracted = os.path.join(DATA_DIR, "ml-latest-small")
    for fname in ["movies.csv", "ratings.csv", "tags.csv", "links.csv"]:
        src = os.path.join(extracted, fname)
        dst = os.path.join(DATA_DIR, fname)
        if os.path.exists(src):
            os.replace(src, dst)
            print(f"  -> {dst}")

    print("Done. movies.csv / ratings.csv / tags.csv / links.csv are now in backend/data/")


if __name__ == "__main__":
    main()
