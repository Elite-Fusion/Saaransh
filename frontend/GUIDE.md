# Building the Saaransh UI — start to finish

This scaffold is a working starting point, not the finished product. It's wired
so **every screen fetches from your real FastAPI backend** — there is no mock
data anywhere, on purpose. Where a backend endpoint doesn't exist yet (Phase 7
similarity, Phase 8 graph, Phase 9 voice, Phase 10 auth per your README), the
matching screen renders an honest loading/error/empty state instead of fake
numbers, and is marked with a `TODO` comment pointing at the exact gap.

## 0. What's already scaffolded

```
saaransh-frontend/
├── src/api/          client.js, dashboard.js, cases.js, ai.js   — all real fetch calls
├── src/hooks/         useFetch.js                                — loading/error/data, no mock fallback
├── src/components/    Card.jsx, StatusStates.jsx                 — Loading / Error / Empty primitives
├── src/layout/        Sidebar.jsx, Topbar.jsx                    — nav from the mockup
├── src/pages/         Dashboard (fully wired), Cases, FirIntake, AIAssistant,
│                       MapIntelligence, CrossCaseLinker, Analytics, + 4 stubs
└── src/App.jsx        router
```

Colors, spacing and the nav structure were taken directly from your screenshot
(`tailwind.config.js` → `brand` = the Saaransh green, `risk` = the map's
red→green risk scale, `ink` = the neutral grays).

## 1. Install and run

```bash
cd saaransh-frontend
npm install
cp .env.example .env      # point VITE_API_BASE_URL at your running backend
npm run dev
```

The backend must be running (`uvicorn backend.main:app --reload`) and
CORS must allow `http://localhost:5173` — add that origin to your FastAPI
`CORSMiddleware` if you haven't already, or every fetch call will fail
with a browser CORS error, not a 4xx/5xx you can debug from the network tab.

## 2. Confirm the real endpoint shapes first

Before writing a single component, open `http://localhost:8000/docs` and
walk through each router the README lists:

- `GET /api/v1/cases`, `GET /api/v1/cases/{id}` (Phase 3)
- `GET /api/v1/dashboard/*` (Phase 4)
- whatever the Phase 6 investigation route is actually mounted at (the
  top-level README doesn't spell this out — check `backend/ai/README.md`
  or the FastAPI router registration in `backend/main.py`)

Update `src/api/dashboard.js`, `cases.js`, `ai.js` to match the **exact**
paths, param names, and response field names your backend returns. I made
reasonable guesses (`total_firs`, `crime_types`, etc.) — treat every field
name in `Dashboard.jsx` as a placeholder to verify against a real response,
not a contract.

## 3. Build order (do it in this order, not screen-by-screen at random)

1. **Sidebar/Topbar** — already done, but sanity check active-route styling.
2. **Dashboard** — the 5 stat cards first (`/dashboard/summary`), since it's
   the simplest possible "real data renders" proof. Get this returning real
   numbers before touching anything else.
3. **Cases list** — table + search, `GET /cases`. This gives you a case ID
   to test the detail/similarity/linking screens with.
4. **FIR intake form** — steps 2–4 (Complainant, Incident, Suspect) are
   currently `EmptyBlock` placeholders; build each step's fields once you've
   confirmed the write endpoint and payload shape with the backend team
   (the README only documents **read-only** Phase 3 endpoints — case
   creation isn't in scope yet as far as the README shows).
5. **AI Assistant** — once `/ai/investigate` (or whatever it's actually
   called) is confirmed, the chat page already posts the question and
   renders `explanation` + `confidence`. Extend it to also render
   `supporting_evidence` as clickable case chips, and `raw_sql`/`columns`
   in a collapsible "show your work" panel for officers who want to audit
   the query — the README makes a point of "every response cites the cases
   it relied on," so surface that, don't bury it.
6. **Map Intelligence** — this is the biggest lift. You need a Karnataka
   district GeoJSON (not something the backend serves — source it
   separately) plus a real risk-score-per-district payload to color it.
   Recommended libs: `react-simple-maps` (SVG, simplest) or MapLibre GL
   (if you want zoom/pan like the mockup's + / − controls). Don't build
   this until the backend actually returns per-district risk numbers —
   there's nothing to encode as color otherwise.
7. **Cross Case Linker** — same story, blocked on Phase 8 (Neo4j). Once
   `/cases/{id}/links` exists, swap the raw JSON dump in
   `CrossCaseLinker.jsx` for an actual force-directed graph (e.g. `d3-force`
   or `react-force-graph`) matching the mockup's radial layout.
8. **Analytics / Alerts / Reports / Users / Settings** — stubs only; build
   these last, once their backing endpoints exist.

## 4. "No mock data" — how this is enforced structurally, not just by promise

- `useFetch` (in `src/hooks/useFetch.js`) has **no fallback branch**. If the
  fetch throws, `error` is set and `data` stays `null` — there's no code
  path that substitutes a canned object.
- Every page imports `LoadingBlock` / `ErrorBlock` / `EmptyBlock` from
  `src/components/StatusStates.jsx` and is required to render one of the
  three whenever `data` isn't populated. When you add a new page, keep this
  pattern — it's what stops "just hardcode something so it looks done"
  from creeping in during a crunch.
- Anywhere I don't yet know the backend's field names, I left a
  `JSON.stringify(data, null, 2)` dump instead of guessing at a polished
  layout with invented field names — that would silently become mock data
  the moment the real response doesn't match my guess.

## 5. Design tokens pulled from your mockup

| Token | Value | Used for |
|---|---|---|
| `brand-500` | `#1a9d5c` | primary buttons, active nav, links |
| `risk.veryhigh → verylow` | `#dc2626 → #22c55e` | risk map legend, delta arrows |
| `ink-900/700/500/300/100` | slate scale | text, borders, backgrounds |
| Font | Inter | matches the mockup's grotesk sans |
| Card | `rounded-xl2` (16px) + `shadow-card` | every panel in the mockup |

## 6. Things to double check against the live backend before demo day

- CORS origin allow-list includes your Vite dev URL and prod URL.
- `VITE_API_BASE_URL` is set correctly per environment (`.env`, `.env.production`).
- Every "TODO" comment in `src/api/*.js` and the pages that reference
  Phase 7/8/9/10 features — resolve or explicitly descope before the demo,
  since those are the screens most likely to still be showing empty states.
