#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RadioJavan - Minimal CLI
Takes only a song title and returns 10 recommendations.

Example usage:
  python radiojavan_cli_min.py "Song Name"
"""

import argparse
import difflib
import os
import pickle
import sys
from typing import Tuple, Optional, List

import pandas as pd


CSV_PATH = "./api/models/data/RadioJavan_Top.csv"
MODEL_PATH = "./api/models/fainal_model/model.pkl"  # same as your model path


def load_data(csv_path: str, model_path: str):
    if not os.path.exists(csv_path):
        print(f"[Error] CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(2)
    if not os.path.exists(model_path):
        print(f"[Error] Model (pickle) file not found: {model_path}", file=sys.stderr)
        sys.exit(2)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[Error] Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(2)

    df = df.drop_duplicates()

    try:
        with open(model_path, "rb") as f:
            similarity = pickle.load(f)
    except Exception as e:
        print(f"[Error] Failed to load model: {e}", file=sys.stderr)
        sys.exit(2)

    indices = pd.Series(df.index, index=df["musicName"]).drop_duplicates()
    return df, indices, similarity


def resolve_title(
    raw_title: str, df: pd.DataFrame, max_suggestions: int = 7
) -> Tuple[Optional[str], List[str]]:
    names = pd.unique(df["musicName"].astype(str))
    lower_map = {name.lower(): name for name in names}

    if raw_title.lower() in lower_map:
        return lower_map[raw_title.lower()], []

    suggestions = difflib.get_close_matches(
        raw_title, names.tolist(), n=max_suggestions, cutoff=0.6
    )
    return None, suggestions


def radio_javan_recommendation(
    title: str, df: pd.DataFrame, indices: pd.Series, similarity
) -> pd.DataFrame:
    index = indices[title]
    similarity_scores = list(enumerate(list(similarity[index])))
    similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
    similarity_scores = similarity_scores[1 : 10 + 1]  # top 10 results

    target_indices = [i for i, _ in similarity_scores]
    out = df[["musicName", "artistName"]].iloc[target_indices].copy()
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def main():
    parser = argparse.ArgumentParser(
        prog="radiojavan_cli_min",
        description="Takes only a song title and returns 10 recommendations.",
    )
    parser.add_argument("title", type=str, help="Song title (preferably in quotes)")
    args = parser.parse_args()

    df, indices, similarity = load_data(CSV_PATH, MODEL_PATH)
    matched, suggestions = resolve_title(args.title, df)

    if matched is None:
        if suggestions:
            matched = suggestions[0]
            print(
                f'[Info] Exact title not found. Closest match selected: "{matched}"',
                file=sys.stderr,
            )
        else:
            print(f'[Error] Title not found: "{args.title}"', file=sys.stderr)
            sys.exit(1)

    try:
        recs = radio_javan_recommendation(matched, df, indices, similarity)
    except KeyError:
        print(
            "[Error] The selected title is not present in the index mapping. "
            "Make sure the CSV and model are aligned.",
            file=sys.stderr,
        )
        sys.exit(2)

    with pd.option_context("display.max_colwidth", None):
        print(recs.to_string(index=False))


if __name__ == "__main__":
    main()
