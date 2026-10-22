import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app, get_recommender
from api.recommender import Recommender

SONGS = [
    ("Gentleman", "Sasy", 900),
    ("Nakoni Bavar", "Zedbazi", 800),
    ("Mr. Lodeh", "Amir Tataloo", 700),
    ("Darya", "Masih", 600),
    ("Doctor", "Sasy", 500),
    ("Darya", "Shadmehr Aghili", 400),
]


@pytest.fixture
def recommender():
    df = pd.DataFrame(SONGS, columns=["musicName", "artistName", "Radiojavan_play"])
    n = len(df)
    sim = np.eye(n)
    # Gentleman -> Doctor, Mr. Lodeh, Nakoni Bavar, Darya(Masih), Darya(Shadmehr)
    for idx, score in zip([4, 2, 1, 3, 5], [0.9, 0.8, 0.7, 0.6, 0.5]):
        sim[0, idx] = sim[idx, 0] = score
    sim[3, 5] = sim[5, 3] = 0.95
    return Recommender(df, sim)


@pytest.fixture
def client(recommender):
    app.dependency_overrides[get_recommender] = lambda: recommender
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "songs": len(SONGS)}


def test_search_by_title_ranks_prefix_first(client):
    res = client.get("/api/songs", params={"q": "d"})
    assert res.status_code == 200
    titles = [s["title"] for s in res.json()]
    # "Darya", "Doctor", "Darya" start with d; "Mr. Lodeh" only contains it.
    assert titles[:3] == ["Darya", "Doctor", "Darya"]
    assert "Mr. Lodeh" in titles


def test_search_by_artist(client):
    res = client.get("/api/songs", params={"q": "sasy"})
    assert [s["title"] for s in res.json()] == ["Gentleman", "Doctor"]


def test_search_respects_limit(client):
    res = client.get("/api/songs", params={"q": "", "limit": 2})
    assert len(res.json()) == 2


def test_search_rejects_invalid_limit(client):
    assert client.get("/api/songs", params={"limit": 0}).status_code == 422


def test_get_song(client):
    res = client.get("/api/songs/0")
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Gentleman"
    assert body["artist"] == "Sasy"
    assert body["plays"] == 900
    assert body["likes"] is None


def test_get_song_not_found(client):
    assert client.get("/api/songs/999").status_code == 404
    assert client.get("/api/songs/-1").status_code == 404


def test_recommend_by_id_orders_by_score_and_excludes_self(client):
    res = client.get("/api/songs/0/recommendations", params={"k": 3})
    assert res.status_code == 200
    body = res.json()
    assert body["song"]["title"] == "Gentleman"
    recs = body["recommendations"]
    assert [r["title"] for r in recs] == ["Doctor", "Mr. Lodeh", "Nakoni Bavar"]
    assert [r["score"] for r in recs] == pytest.approx([0.9, 0.8, 0.7])
    assert all(r["id"] != 0 for r in recs)


def test_recommend_distinguishes_duplicate_titles(client):
    res = client.get("/api/songs/5/recommendations", params={"k": 1})
    body = res.json()
    assert body["song"]["artist"] == "Shadmehr Aghili"
    assert body["recommendations"][0]["artist"] == "Masih"


def test_recommend_by_id_not_found(client):
    assert client.get("/api/songs/42/recommendations").status_code == 404


def test_recommend_by_title_case_insensitive(client):
    res = client.get("/api/recommendations", params={"title": "gentleman", "k": 2})
    assert res.status_code == 200
    body = res.json()
    assert body["song"]["id"] == 0
    assert [r["title"] for r in body["recommendations"]] == ["Doctor", "Mr. Lodeh"]


def test_recommend_by_title_fuzzy_match(client):
    res = client.get("/api/recommendations", params={"title": "Gentlemen"})
    assert res.status_code == 200
    assert res.json()["song"]["title"] == "Gentleman"


def test_recommend_by_title_not_found(client):
    res = client.get("/api/recommendations", params={"title": "zzzzzz"})
    assert res.status_code == 404


def test_recommender_rejects_mismatched_matrix():
    df = pd.DataFrame(SONGS[:2], columns=["musicName", "artistName", "Radiojavan_play"])
    with pytest.raises(ValueError):
        Recommender(df, np.eye(3))


def test_real_model_files_are_aligned():
    rec = get_recommender()
    assert len(rec) > 0
    song_id = rec.resolve_title("Gentleman")
    assert song_id is not None
    assert len(rec.recommend(song_id, 10)) == 10
