const formatPlays = new Intl.NumberFormat("en", { notation: "compact" });

export default function RecommendationList({ song, recommendations, onSelect }) {
  return (
    <section className="results" aria-label={`Recommendations for ${song.title}`}>
      <h2>
        Because you like <em>{song.title}</em>
        <span className="artist"> · {song.artist}</span>
      </h2>
      <ol className="rec-list">
        {recommendations.map((rec, i) => (
          <li key={rec.id}>
            <span className="rank">{i + 1}</span>
            <button
              type="button"
              className="rec-main"
              onClick={() => onSelect(rec)}
              title={`Get recommendations for ${rec.title}`}
            >
              <span className="title">{rec.title}</span>
              <span className="artist">{rec.artist}</span>
            </button>
            {rec.plays != null && (
              <span className="plays">{formatPlays.format(rec.plays)} plays</span>
            )}
            <span
              className="score"
              aria-label={`Similarity ${Math.round(rec.score * 100)}%`}
            >
              <span className="score-bar" style={{ width: `${Math.max(rec.score, 0) * 100}%` }} />
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
