# PROJECT_SPEC.md — CivicLens

**Source of truth for architecture, schema, and contracts.** Behavioral rules live in `CLAUDE.md`.

> **Stack decisions below are defaults chosen for a 24-hour build.** If the team has already committed to a different stack, change §2 first and flag it in `DEVLOG.md` before writing code.

---

## 1. Product

Citizens photograph civic issues (potholes, garbage, broken streetlights, waterlogging). AI classifies the issue type, estimates severity, and detects duplicate reports of the same physical problem. A priority score ranks everything on an authority dashboard with a map. Authorities update status; citizens track resolution.

### Core flow

```
Citizen uploads photo + GPS
        ↓
Backend stores report (status=REPORTED)
        ↓
AI pipeline: classify category → severity → embed image → dedup check
        ↓
Duplicate? → link to canonical report, bump its report_count
Not duplicate? → new canonical report
        ↓
Priority score computed
        ↓
Authority dashboard: sorted list + map + filters
        ↓
Status transitions → citizen sees updates
```

### Success criteria for demo

1. Submit a report from the citizen UI with a real photo → it appears on the dashboard within 5 seconds with a category, severity, and priority score.
2. Submit a near-identical second photo at a nearby location → it is flagged as a duplicate and merged, not listed twice.
3. Authority changes status → citizen tracking view reflects it.
4. Map shows all reports, colored by priority.

---

## 2. Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2 | Same language as AI layer, auto OpenAPI docs for the team |
| DB | SQLite (dev + demo), Postgres-ready via SQLAlchemy | Zero setup cost; swap the URL for Postgres if deploying |
| AI | PyTorch + `open_clip` or HuggingFace `transformers` CLIP, Pillow, NumPy | Zero-shot classification + embeddings from one model |
| Vector search | NumPy cosine similarity in-memory, embeddings persisted as BLOB | Hackathon scale (<10k reports). No vector DB needed. |
| Frontend | React 18 + Vite + TypeScript + TailwindCSS | Fast, no config rabbit holes |
| Map | `react-leaflet` + OpenStreetMap tiles | **No API key, no billing** — avoids the Google Maps key-leak risk entirely |
| Auth | JWT (`python-jose`), `passlib[bcrypt]` | Minimal, stateless |
| Deploy | Docker Compose locally; backend → Render/Railway, frontend → Vercel/Netlify | Free tiers, fast |

**Verify actual installed versions before using version-sensitive APIs** (SQLAlchemy 2.x and Pydantic v2 differ substantially from 1.x).

---

## 3. Repo Structure

```
civiclens/
├── CLAUDE.md
├── PROJECT_SPEC.md
├── DEVLOG.md
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── scripts/
│   └── check-secrets.sh
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py            # FastAPI app, CORS, router mounting, /health
│       ├── config.py          # env loading + validation
│       ├── database.py        # engine, SessionLocal, get_db
│       ├── models.py          # SQLAlchemy ORM
│       ├── schemas.py         # Pydantic request/response models
│       ├── auth.py            # hashing, JWT, current_user/require_authority deps
│       ├── scoring.py         # priority score (SHARED CONSTANTS LIVE HERE)
│       ├── storage.py         # image save/validate
│       └── routers/
│           ├── auth.py
│           ├── reports.py
│           └── dashboard.py
├── ai/
│   ├── requirements.txt
│   ├── classifier.py          # zero-shot category + confidence
│   ├── severity.py            # severity estimation
│   ├── embeddings.py          # CLIP image embedding
│   ├── dedup.py               # duplicate detection
│   ├── pipeline.py            # analyze_image() — the ONLY entry point backend calls
│   └── tests/
└── frontend/
    ├── package.json
    ├── .env.example
    └── src/
        ├── api/client.ts      # single axios/fetch wrapper, base URL from env
        ├── types.ts           # mirrors backend schemas
        ├── pages/
        │   ├── Report.tsx     # citizen submit
        │   ├── Track.tsx      # citizen "my reports"
        │   ├── Dashboard.tsx  # authority list + filters
        │   └── MapView.tsx
        └── components/
```

---

## 4. Shared Constants (frozen — `backend/app/scoring.py`, mirrored in `ai/`)

```python
CATEGORIES = [
    "pothole", "garbage_dump", "broken_streetlight", "waterlogging",
    "damaged_road", "sewage_overflow", "broken_footpath",
    "fallen_tree", "stray_animals", "illegal_dumping", "other",
]

# How dangerous the category is regardless of visual severity (1-5)
CATEGORY_CRITICALITY = {
    "sewage_overflow": 5, "waterlogging": 5, "fallen_tree": 5,
    "pothole": 4, "damaged_road": 4, "broken_streetlight": 4,
    "garbage_dump": 3, "illegal_dumping": 3, "broken_footpath": 3,
    "stray_animals": 2, "other": 2,
}

STATUSES = ["reported", "acknowledged", "in_progress", "resolved", "rejected"]

# Duplicate detection thresholds
DUP_SIMILARITY_THRESHOLD = 0.86   # cosine similarity on CLIP embeddings
DUP_RADIUS_METERS        = 100
DUP_TIME_WINDOW_DAYS     = 30

# Priority weights (must sum to 1.0)
W_SEVERITY    = 0.40
W_CRITICALITY = 0.25
W_REPORTS     = 0.20
W_AGE         = 0.15
```

### Priority score formula

```
priority = 100 * (
    W_SEVERITY    * (severity / 5)
  + W_CRITICALITY * (CATEGORY_CRITICALITY[category] / 5)
  + W_REPORTS     * min(report_count / 10, 1.0)
  + W_AGE         * min(age_days / 14, 1.0)
)
```

Range 0–100. Recompute on: creation, duplicate merge, upvote, and on dashboard read if `age_days` changed. Rounded to 1 decimal.

**One implementation only** — the frontend never recomputes it.

---

## 5. Database Schema

```sql
users
  id            INTEGER PK
  name          TEXT NOT NULL
  email         TEXT UNIQUE NOT NULL
  password_hash TEXT NOT NULL
  role          TEXT NOT NULL DEFAULT 'citizen'   -- citizen | authority
  created_at    DATETIME NOT NULL

reports
  id                INTEGER PK
  user_id           INTEGER FK → users.id
  image_path        TEXT NOT NULL
  latitude          REAL NOT NULL
  longitude         REAL NOT NULL
  address           TEXT
  description       TEXT
  category          TEXT NOT NULL          -- from CATEGORIES
  ai_confidence     REAL NOT NULL          -- 0.0-1.0
  severity          INTEGER NOT NULL       -- 1-5
  status            TEXT NOT NULL DEFAULT 'reported'
  priority_score    REAL NOT NULL
  report_count      INTEGER NOT NULL DEFAULT 1   -- 1 + merged duplicates + upvotes
  is_duplicate_of   INTEGER FK → reports.id NULL -- NULL = canonical
  created_at        DATETIME NOT NULL
  updated_at        DATETIME NOT NULL
  INDEX (status), INDEX (category), INDEX (is_duplicate_of)

report_embeddings
  report_id  INTEGER PK FK → reports.id
  vector     BLOB NOT NULL      -- float32 numpy array, L2-normalized
  dim        INTEGER NOT NULL

status_history
  id          INTEGER PK
  report_id   INTEGER FK → reports.id
  old_status  TEXT
  new_status  TEXT NOT NULL
  changed_by  INTEGER FK → users.id
  note        TEXT
  created_at  DATETIME NOT NULL
```

Store embeddings L2-normalized so similarity is a plain dot product.

---

## 6. API Contract (frozen)

Base: `/api/v1`. All errors: `{"detail": "message"}` with a correct status code.

### Auth
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/register` | `{name, email, password, role?}` | `{access_token, token_type, user}` |
| POST | `/auth/login` | `{email, password}` | `{access_token, token_type, user}` |
| GET | `/auth/me` | — | `User` |

### Reports
| Method | Path | Notes |
|---|---|---|
| POST | `/reports` | **multipart/form-data**: `image` (file), `latitude`, `longitude`, `description?`, `address?`. Runs AI pipeline. Returns `ReportOut` + `duplicate_of` if merged. |
| GET | `/reports` | Query: `status`, `category`, `min_priority`, `sort` (`priority`\|`recent`), `bbox=minLat,minLng,maxLat,maxLng`, `limit`, `offset`. **Excludes duplicates by default** (`include_duplicates=false`). |
| GET | `/reports/{id}` | Includes `duplicates[]` and `status_history[]` |
| GET | `/reports/mine` | Auth required. Citizen's own reports. |
| PATCH | `/reports/{id}/status` | **Authority role only.** `{status, note?}`. Writes `status_history`. |
| POST | `/reports/{id}/upvote` | Increments `report_count`, recomputes priority. One per user. |

### Dashboard
| Method | Path | Returns |
|---|---|---|
| GET | `/dashboard/stats` | `{total, by_status{}, by_category{}, avg_resolution_hours, high_priority_count}` |

### System
| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{"status":"ok","db":"ok"}` |

### `ReportOut` shape

```json
{
  "id": 1,
  "image_url": "/uploads/uuid.jpg",
  "latitude": 28.4595, "longitude": 77.0266,
  "address": "Sector 23A, Gurugram",
  "description": "Large pothole near gate",
  "category": "pothole",
  "ai_confidence": 0.87,
  "severity": 4,
  "status": "reported",
  "priority_score": 72.4,
  "report_count": 3,
  "is_duplicate_of": null,
  "created_at": "2026-08-13T09:12:00Z",
  "updated_at": "2026-08-13T09:12:00Z"
}
```

Never return `password_hash`, raw filesystem paths, or user emails on public endpoints.

---

## 7. AI Layer

Single entry point the backend calls — nothing else:

```python
# ai/pipeline.py
def analyze_image(image_path: str, lat: float, lng: float) -> AnalysisResult:
    """
    Returns:
      category: str          # one of CATEGORIES
      confidence: float      # 0.0-1.0
      severity: int          # 1-5
      embedding: np.ndarray  # float32, L2-normalized
    Must NEVER raise. On any internal failure return the safe fallback:
      category="other", confidence=0.0, severity=3, embedding=zeros
    """
```

### 7.1 Classification — zero-shot CLIP

No training. Encode text prompts once at startup, compare against the image embedding:

```python
PROMPTS = {
    "pothole": "a photo of a pothole in a road",
    "garbage_dump": "a photo of a pile of garbage on the street",
    "broken_streetlight": "a photo of a damaged or broken street light",
    "waterlogging": "a photo of a flooded waterlogged street",
    # ... one natural-language prompt per category
}
```

Take softmax over similarities → `category` = argmax, `confidence` = max prob. If `confidence < 0.25`, return `"other"`.

### 7.2 Severity (1–5)

Combine signals — do not train a model:

| Signal | Contribution |
|---|---|
| Category criticality baseline | `CATEGORY_CRITICALITY[category]` |
| Classification confidence | high confidence nudges toward the extremes |
| Affected-area proxy | fraction of image the issue region occupies (heuristic: segmentation or brightness/edge density) |
| Duplicate count | more independent reports of the same spot → higher severity |

Clamp to 1–5. Document the exact formula you implement in `ai/severity.py` docstring, and state which parts are heuristic.

### 7.3 Duplicate detection

Three gates, **all must pass**:

1. **Geo:** Haversine distance ≤ `DUP_RADIUS_METERS` (100 m)
2. **Time:** existing report created within `DUP_TIME_WINDOW_DAYS` (30 d)
3. **Visual:** cosine similarity ≥ `DUP_SIMILARITY_THRESHOLD` (0.86)

Also require `category` match. Filter by geo+time **first** (cheap SQL), then compute similarity only against that small candidate set — never against the whole table.

On match: set `is_duplicate_of` to the canonical report's id, increment canonical `report_count`, recompute canonical priority. Return both ids so the UI can say "merged with existing report #N".

### 7.4 Performance

- Load the CLIP model **once** at app startup (module-level singleton), not per request.
- Resize images to the model input size before encoding.
- Target < 3 s end-to-end per submission on CPU. If slower, run the AI step in a FastAPI `BackgroundTask` and return the report immediately with `category="analyzing"`, then patch it.

---

## 8. Frontend Requirements

### Pages

| Page | Contents |
|---|---|
| `/report` | Photo upload (camera capture on mobile), auto-GPS via `navigator.geolocation` with manual map-pin fallback, optional description, submit → result card showing detected category/severity, or "merged with report #N" |
| `/track` | Citizen's own reports, status timeline per report |
| `/dashboard` | Authority-only. Sorted-by-priority list, filters (status/category/min priority), status update control, stats cards |
| `/map` | Leaflet map, markers colored by priority (green <40, amber 40–70, red >70), popup with thumbnail + category + priority, click → detail |

### Rules

- One API client (`src/api/client.ts`); base URL from `VITE_API_BASE_URL`. No `fetch` calls scattered in components.
- Loading and error states on every async view. No silent failures, no infinite spinners.
- Types in `src/types.ts` mirror the backend Pydantic schemas exactly.
- Mobile-first — the demo will be shown on a phone.
- No secrets in frontend env (see `CLAUDE.md` §1.2).

---

## 9. 24-Hour Milestones

Ship in this order. **Do not start a phase until the previous one runs end to end.**

| Phase | Hours | Deliverable | Gate |
|---|---|---|---|
| **P0 — Skeleton** | 0–2 | Repo, `.gitignore`, `.env.example`, secret-scan hook, FastAPI boots with `/health`, Vite app renders, DB tables created | `curl /health` → 200; `npm run build` clean |
| **P1 — Vertical slice** | 2–6 | `POST /reports` (no AI — hardcode category/severity), image saved, `GET /reports`, citizen submit form posts successfully | Submit from UI → row in DB → shows in list |
| **P2 — AI online** | 6–11 | CLIP loads at startup, `analyze_image()` wired into `POST /reports`, embeddings persisted, priority score live | Real photo → correct-ish category + priority on dashboard |
| **P3 — Dedup + dashboard** | 11–16 | Duplicate detection, merge logic, authority dashboard with sort/filter, status update + history | Two similar photos 50 m apart → one entry, `report_count=2` |
| **P4 — Map + tracking** | 16–20 | Leaflet map with priority-colored markers, citizen tracking view, auth + role gating enforced | All 4 demo success criteria pass |
| **P5 — Harden** | 20–22 | Error states, input validation, AI failure fallback verified, seed 15–20 demo reports, `README.md` | Kill the AI module → submissions still succeed |
| **P6 — Deploy + demo** | 22–24 | Deploy, env vars set in platform UI (not committed), rehearse the demo path twice, final secret scan | `bash scripts/check-secrets.sh` clean; live URL works |

### Parallelization

- Hours 0–2: M4 does P0 solo, everyone else sets up their local env.
- Hours 2–11: M1 builds `ai/` against sample images standalone (no backend dependency). M2 builds backend with a stub `analyze_image()`. M3 builds UI against mock JSON matching §6. **The API contract is what lets them work in parallel — freeze it at hour 2.**
- Hour 11: M4 does the real integration. This is the highest-risk moment — budget for it.

### Demo seed data

Pre-seed 15–20 reports across Gurugram coordinates spanning all statuses and priority bands **before** the demo. Live demo relies on a fresh submission only for the flow, not for populating the dashboard.

---

## 10. Environment Variables

Backend (`.env`, gitignored):
```
SECRET_KEY=            # 32+ random bytes — generate, never reuse an example
DATABASE_URL=sqlite:///./civiclens.db
UPLOAD_DIR=./uploads
MAX_UPLOAD_MB=5
ALLOWED_ORIGINS=http://localhost:5173
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Frontend (`frontend/.env`, gitignored — **public values only**):
```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

`config.py` must **fail loudly at startup** if `SECRET_KEY` is missing. No fallback default.

---

## 11. Open Decisions — confirm before building

1. **Stack** — confirm FastAPI + React + Leaflet, or specify replacements.
2. **Auth depth** — full JWT auth, or a simplified role toggle for the demo?
3. **Deploy target** — Render/Railway/Vercel, or local-only demo?
4. **Severity ground truth** — heuristic only (as specced), or does M1 have a labeled dataset to do better?

If unanswered, proceed with the defaults above and record the assumption in `DEVLOG.md`.
