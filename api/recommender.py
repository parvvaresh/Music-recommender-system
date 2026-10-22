import difflib
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd


class Recommender:
    """Wraps the song catalogue and the pre-computed similarity matrix.

    Songs are addressed by their row position in the CSV (``id``), because
    titles are not unique (the same title can belong to several artists).
    """

    def __init__(self, df: pd.DataFrame, similarity: np.ndarray):
        df = df.reset_index(drop=True)
        similarity = np.asarray(similarity)
        if similarity.shape != (len(df), len(df)):
            raise ValueError(
                f"Similarity matrix shape {similarity.shape} does not match "
                f"{len(df)} songs in the catalogue"
            )
        self.df = df
        self.similarity = similarity
        self._titles = df["musicName"].astype(str)
        self._titles_lower = self._titles.str.lower()
        self._artists_lower = df["artistName"].astype(str).str.lower()

    @classmethod
    def from_files(cls, csv_path: Path, model_path: Path) -> "Recommender":
        df = pd.read_csv(csv_path)
        with open(model_path, "rb") as f:
            similarity = pickle.load(f)
        return cls(df, similarity)

    def __len__(self) -> int:
        return len(self.df)

    def song(self, song_id: int) -> dict:
        row = self.df.iloc[song_id]
        return {
            "id": int(song_id),
            "title": str(row["musicName"]),
            "artist": str(row["artistName"]),
            "plays": _optional_int(row.get("Radiojavan_play")),
            "likes": _optional_int(row.get("Radiojavan_likes")),
            "popularity": _optional_int(row.get("popularity")),
            "published": _optional_str(row.get("pubdate")),
        }

    def has_song(self, song_id: int) -> bool:
        return 0 <= song_id < len(self.df)

    def search(self, query: str, limit: int = 10) -> List[dict]:
        """Case-insensitive substring search over titles and artists.

        Title prefix matches rank first, then other title matches, then
        artist matches; ties are broken by catalogue order (play count).
        """
        q = query.strip().lower()
        if not q:
            return [self.song(i) for i in range(min(limit, len(self.df)))]

        prefix = self._titles_lower.str.startswith(q, na=False)
        in_title = self._titles_lower.str.contains(q, regex=False, na=False)
        in_artist = self._artists_lower.str.contains(q, regex=False, na=False)

        ids = (
            list(self.df.index[prefix])
            + list(self.df.index[in_title & ~prefix])
            + list(self.df.index[in_artist & ~in_title])
        )
        return [self.song(i) for i in ids[:limit]]

    def resolve_title(self, title: str) -> Optional[int]:
        """Exact (case-insensitive) title match, else the closest fuzzy match."""
        matches = self.df.index[self._titles_lower == title.strip().lower()]
        if len(matches):
            return int(matches[0])

        close = difflib.get_close_matches(
            title, pd.unique(self._titles).tolist(), n=1, cutoff=0.6
        )
        if close:
            return int(self.df.index[self._titles == close[0]][0])
        return None

    def recommend(self, song_id: int, k: int = 10) -> List[dict]:
        scores = self.similarity[song_id]
        # Stable sort so equal scores keep catalogue order, matching the CLI.
        order = np.argsort(-scores, kind="stable")
        results = []
        for idx in order:
            if idx == song_id:
                continue
            results.append({**self.song(int(idx)), "score": float(scores[idx])})
            if len(results) == k:
                break
        return results


def _optional_int(value) -> Optional[int]:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _optional_str(value) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    return str(value)
