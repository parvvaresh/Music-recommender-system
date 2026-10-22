const BASE_URL = import.meta.env.VITE_API_URL ?? "";

async function request(path, params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${BASE_URL}${path}${query ? `?${query}` : ""}`);
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Non-JSON error body; keep the generic message.
    }
    throw new Error(message);
  }
  return res.json();
}

export function searchSongs(q, limit = 8) {
  return request("/api/songs", { q, limit });
}

export function getRecommendations(songId, k = 10) {
  return request(`/api/songs/${songId}/recommendations`, { k });
}
