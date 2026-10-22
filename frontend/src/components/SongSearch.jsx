import { useEffect, useId, useState } from "react";
import { searchSongs } from "../api.js";

const DEBOUNCE_MS = 250;

export default function SongSearch({ onSelect }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState(null);
  const listId = useId();

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setResults([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(() => {
      searchSongs(q)
        .then((songs) => {
          if (cancelled) return;
          setResults(songs);
          setError(null);
          setOpen(true);
        })
        .catch((err) => !cancelled && setError(err.message));
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  function choose(song) {
    setQuery(song.title);
    setOpen(false);
    onSelect(song);
  }

  return (
    <div className="search">
      <label htmlFor={`${listId}-input`} className="search-label">
        Search a song or artist
      </label>
      <input
        id={`${listId}-input`}
        type="search"
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls={listId}
        autoComplete="off"
        placeholder="e.g. Gentleman, Masih…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setOpen(true)}
      />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {open && query.trim() && results.length > 0 && (
        <ul id={listId} role="listbox" className="suggestions">
          {results.map((song) => (
            <li key={song.id} role="option" aria-selected="false">
              <button type="button" onClick={() => choose(song)}>
                <span className="title">{song.title}</span>
                <span className="artist">{song.artist}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
