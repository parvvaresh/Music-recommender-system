import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";

const GENTLEMAN = { id: 0, title: "Gentleman", artist: "Sasy", plays: 97011366 };
const DOCTOR = { id: 4, title: "Doctor", artist: "Sasy", plays: 1200000 };
const MOOHAT = { id: 7, title: "Moohat", artist: "Mohsen Yeganeh", plays: null };

function jsonResponse(body, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

// Routes fetch calls by path so tests read like a tiny fake backend.
function mockApi(routes) {
  const fetchMock = vi.fn((url) => {
    const { pathname } = new URL(url, "http://localhost");
    const handler = routes[pathname];
    if (!handler) return jsonResponse({ detail: "Not Found" }, 404);
    return handler(url);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders the search box", () => {
  mockApi({});
  render(<App />);
  expect(screen.getByRole("heading", { name: /radiojavan recommender/i })).toBeInTheDocument();
  expect(screen.getByRole("combobox")).toBeInTheDocument();
});

test("searches as the user types and shows suggestions", async () => {
  const fetchMock = mockApi({ "/api/songs": () => jsonResponse([GENTLEMAN]) });
  render(<App />);

  await userEvent.type(screen.getByRole("combobox"), "gent");

  const listbox = await screen.findByRole("listbox");
  expect(within(listbox).getByText("Gentleman")).toBeInTheDocument();
  expect(within(listbox).getByText("Sasy")).toBeInTheDocument();
  // Debounced: one request for the final query, not one per keystroke.
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock.mock.calls[0][0]).toBe("/api/songs?q=gent&limit=8");
});

test("selecting a song shows its recommendations", async () => {
  const fetchMock = mockApi({
    "/api/songs": () => jsonResponse([GENTLEMAN]),
    "/api/songs/0/recommendations": () =>
      jsonResponse({
        song: GENTLEMAN,
        recommendations: [
          { ...DOCTOR, score: 0.92 },
          { ...MOOHAT, score: 0.81 },
        ],
      }),
  });
  render(<App />);

  await userEvent.type(screen.getByRole("combobox"), "gent");
  await userEvent.click(await screen.findByRole("button", { name: /gentleman/i }));

  const results = await screen.findByRole("region", { name: /recommendations for gentleman/i });
  const items = within(results).getAllByRole("listitem");
  expect(items).toHaveLength(2);
  expect(items[0]).toHaveTextContent("Doctor");
  expect(items[0]).toHaveTextContent("1.2M plays");
  expect(within(items[0]).getByLabelText("Similarity 92%")).toBeInTheDocument();
  expect(items[1]).toHaveTextContent("Moohat");
  expect(items[1]).not.toHaveTextContent("plays");
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenLastCalledWith("/api/songs/0/recommendations?k=10");
});

test("clicking a recommendation loads recommendations for that song", async () => {
  mockApi({
    "/api/songs": () => jsonResponse([GENTLEMAN]),
    "/api/songs/0/recommendations": () =>
      jsonResponse({ song: GENTLEMAN, recommendations: [{ ...DOCTOR, score: 0.9 }] }),
    "/api/songs/4/recommendations": () =>
      jsonResponse({ song: DOCTOR, recommendations: [{ ...MOOHAT, score: 0.7 }] }),
  });
  render(<App />);

  await userEvent.type(screen.getByRole("combobox"), "gent");
  await userEvent.click(await screen.findByRole("button", { name: /gentleman/i }));
  await userEvent.click(await screen.findByTitle("Get recommendations for Doctor"));

  const results = await screen.findByRole("region", { name: /recommendations for doctor/i });
  expect(within(results).getByText("Moohat")).toBeInTheDocument();
});

test("shows the API error message when recommendations fail", async () => {
  mockApi({
    "/api/songs": () => jsonResponse([GENTLEMAN]),
    "/api/songs/0/recommendations": () => jsonResponse({ detail: "Song 0 not found" }, 404),
  });
  render(<App />);

  await userEvent.type(screen.getByRole("combobox"), "gent");
  await userEvent.click(await screen.findByRole("button", { name: /gentleman/i }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Song 0 not found");
  expect(screen.queryByRole("region")).not.toBeInTheDocument();
});

test("shows an error when search fails", async () => {
  mockApi({ "/api/songs": () => Promise.resolve(new Response("boom", { status: 500 })) });
  render(<App />);

  await userEvent.type(screen.getByRole("combobox"), "x");

  expect(await screen.findByRole("alert")).toHaveTextContent("Request failed (500)");
});
