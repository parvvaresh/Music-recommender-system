import { useState } from "react";
import { getRecommendations } from "./api.js";
import SongSearch from "./components/SongSearch.jsx";
import RecommendationList from "./components/RecommendationList.jsx";

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function selectSong(song) {
    setLoading(true);
    setError(null);
    try {
      setResult(await getRecommendations(song.id));
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <header>
        <h1>RadioJavan Recommender</h1>
        <p className="subtitle">Pick a song and get 10 similar tracks.</p>
      </header>

      <SongSearch onSelect={selectSong} />

      {loading && <p className="status">Loading recommendations…</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!loading && result && (
        <RecommendationList
          song={result.song}
          recommendations={result.recommendations}
          onSelect={selectSong}
        />
      )}
    </main>
  );
}
