"""
hydrate_comments.py
===================

Retrieves the text of the YouTube comments listed in
``data/comment_ids_labels.tsv`` and writes ``data/comments.tsv``
(id_comentario, comentario, rotulo), the input of ``train_bertimbau.py``.

Why the text is not in the repository: the YouTube API Services Developer
Policies forbid redistributing data obtained through the API (III.G.1) and
limit its storage to 30 days (III.E.4). Only the IDs and labels are published,
and whoever reproduces the work downloads the text with their own API key.
Delete ``data/comments.tsv`` within 30 days.

Comments deleted by their authors or removed by YouTube are no longer returned
by the API; they are reported on the console and left out of the output.

Usage:
    export YOUTUBE_API_KEY="your-key"
    python hydrate_comments.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

API_URL = "https://www.googleapis.com/youtube/v3/comments"
BATCH = 50  # maximum number of IDs per comments.list call


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download comment text from the comment IDs.")
    parser.add_argument("--ids", default=str(DATA_DIR / "comment_ids_labels.tsv"),
                        help="TSV with id_comentario and rotulo (default: data/comment_ids_labels.tsv).")
    parser.add_argument("--output", default=str(DATA_DIR / "comments.tsv"),
                        help="Output TSV (default: data/comments.tsv).")
    parser.add_argument("--api-key", default=os.environ.get("YOUTUBE_API_KEY"),
                        help="YouTube Data API v3 key (default: YOUTUBE_API_KEY environment variable).")
    return parser.parse_args()


def preprocess(text: str) -> str:
    """Same treatment as the annotated dataset: lowercase, no accents, no
    punctuation/emojis and no line breaks."""
    text = unicodedata.normalize("NFD", str(text).lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"[\t\r\n]+", " ", text)


def fetch_batch(ids: list[str], api_key: str) -> dict[str, str]:
    query = urllib.parse.urlencode({
        "part": "snippet",
        "id": ",".join(ids),
        "textFormat": "plainText",
        "key": api_key,
    })
    for attempt in range(5):
        try:
            with urllib.request.urlopen(f"{API_URL}?{query}", timeout=30) as resp:
                payload = json.load(resp)
            return {item["id"]: item["snippet"]["textDisplay"] for item in payload.get("items", [])}
        except urllib.error.HTTPError as e:
            if e.code in (403, 400):
                sys.exit(f"[ERROR] API returned {e.code}: {e.read().decode(errors='replace')}")
            time.sleep(2 ** attempt)
        except urllib.error.URLError:
            time.sleep(2 ** attempt)
    sys.exit("[ERROR] Repeated network failure while querying the API.")


def main() -> int:
    args = parse_args()
    if not args.api_key:
        sys.exit("[ERROR] Provide the key with --api-key or the YOUTUBE_API_KEY environment variable.")

    df = pd.read_csv(args.ids, sep="\t", dtype={"id_comentario": str})
    ids = df["id_comentario"].tolist()

    texts: dict[str, str] = {}
    for start in range(0, len(ids), BATCH):
        texts.update(fetch_batch(ids[start:start + BATCH], args.api_key))
        print(f"\r{min(start + BATCH, len(ids))}/{len(ids)} IDs queried", end="", flush=True)
    print()

    df["comentario"] = df["id_comentario"].map(texts)
    missing = df["comentario"].isna()
    if missing.any():
        print(f"[warning] {missing.sum()} comments are no longer available and were left out.")
    df = df[~missing].copy()
    df["comentario"] = df["comentario"].map(preprocess)

    cols = ["id_comentario", "comentario", "rotulo"] + [c for c in df.columns
                                                         if c not in ("id_comentario", "comentario", "rotulo")]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(args.output, sep="\t", index=False)
    print(f"[OK] {len(df)} comments saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
