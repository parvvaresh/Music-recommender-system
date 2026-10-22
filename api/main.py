"""
RadioJavan recommendation API.

Run locally:
  uvicorn api.main:app --reload
"""

import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.recommender import Recommender

API_DIR = Path(__file__).resolve().parent
CSV_PATH = Path(os.getenv("RJ_CSV_PATH", API_DIR / "models/data/RadioJavan_Top.csv"))
MODEL_PATH = Path(os.getenv("RJ_MODEL_PATH", API_DIR / "models/fainal_model/model.pkl"))
FRONTEND_DIST = API_DIR.parent / "frontend" / "dist"
CORS_ORIGINS = os.getenv("RJ_CORS_ORIGINS", "http://localhost:5173").split(",")


class Song(BaseModel):
    id: int
    title: str
    artist: str
    plays: Optional[int] = None
    likes: Optional[int] = None
    popularity: Optional[int] = None
    published: Optional[str] = None


class Recommendation(Song):
    score: float


class RecommendationResponse(BaseModel):
    song: Song
    recommendations: List[Recommendation]


@lru_cache(maxsize=1)
def get_recommender() -> Recommender:
    return Recommender.from_files(CSV_PATH, MODEL_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on startup if the data or model is missing, but skip the
    # load when tests have swapped in their own recommender.
    if get_recommender not in app.dependency_overrides:
        get_recommender()
    yield


app = FastAPI(title="RadioJavan Recommender API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _get_song_or_404(rec: Recommender, song_id: int) -> dict:
    if not rec.has_song(song_id):
        raise HTTPException(status_code=404, detail=f"Song {song_id} not found")
    return rec.song(song_id)


@app.get("/api/health")
def health(rec: Recommender = Depends(get_recommender)):
    return {"status": "ok", "songs": len(rec)}


@app.get("/api/songs", response_model=List[Song])
def search_songs(
    q: str = Query("", max_length=200, description="Title or artist substring"),
    limit: int = Query(10, ge=1, le=50),
    rec: Recommender = Depends(get_recommender),
):
    return rec.search(q, limit)


@app.get("/api/songs/{song_id}", response_model=Song)
def get_song(song_id: int, rec: Recommender = Depends(get_recommender)):
    return _get_song_or_404(rec, song_id)


@app.get("/api/songs/{song_id}/recommendations", response_model=RecommendationResponse)
def recommend_by_id(
    song_id: int,
    k: int = Query(10, ge=1, le=50),
    rec: Recommender = Depends(get_recommender),
):
    song = _get_song_or_404(rec, song_id)
    return {"song": song, "recommendations": rec.recommend(song_id, k)}


@app.get("/api/recommendations", response_model=RecommendationResponse)
def recommend_by_title(
    title: str = Query(..., min_length=1, max_length=200),
    k: int = Query(10, ge=1, le=50),
    rec: Recommender = Depends(get_recommender),
):
    song_id = rec.resolve_title(title)
    if song_id is None:
        raise HTTPException(status_code=404, detail=f'Title not found: "{title}"')
    return {"song": rec.song(song_id), "recommendations": rec.recommend(song_id, k)}


# Serve the built React app (frontend/dist) when present, so a single
# process can host both the API and the UI in production.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
