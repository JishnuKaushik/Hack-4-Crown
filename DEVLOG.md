# DEVLOG.md — CivicLens

Handoff log. Updated continuously per CLAUDE.md §5.

---

## 2026-08-13 — P0 kickoff: repo scaffold

**Done:**
- Moved `check-secrets.sh` → `scripts/check-secrets.sh` per PROJECT_SPEC §3 layout (was at repo root).
- Installed it as `.git/hooks/pre-commit` (executable), verified it runs clean on empty stage.
- Created directory scaffold: `backend/app/routers/`, `ai/tests/`, `frontend/src/{api,pages,components}/`.
- Created this `DEVLOG.md`.

**Root cause fixes:** none yet.

**Assumptions:**
- Open decisions from PROJECT_SPEC.md §11 proceeding with spec defaults (not yet confirmed by user):
  1. Stack: FastAPI + React + Leaflet + SQLite — proceeding as specced.
  2. Auth depth: full JWT auth as specced.
  3. Deploy target: not yet decided, deferred to P6.
  4. Severity ground truth: heuristic only (no labeled dataset available) — proceeding as specced.
- User confirmed workflow: auto-commit per verified unit on feat/fix branches, run phases P0→P6 autonomously, self-verify gates, only stop on 3-failed-attempts or genuine blocking decision.

**Known Issues:** none yet.

**Next:** backend skeleton — config.py, database.py, models.py, main.py with /health.

---

## 2026-08-13 — P0: backend skeleton

**Done:**
- `backend/app/config.py`: Pydantic-settings `Settings`, fails loudly (raises `ValidationError`) if `SECRET_KEY` is missing or a known placeholder. No hardcoded default.
- `backend/app/database.py`: SQLAlchemy 2.x engine/session, `Base(DeclarativeBase)`, `get_db()` generator dependency.
- `backend/app/scoring.py`: frozen shared constants + `compute_priority_score()` per PROJECT_SPEC §4. Sanity-checked with 3 manual cases (low/mid/max) — output correctly bounded 0–100.
- `backend/app/models.py`: `User`, `Report`, `ReportEmbedding`, `StatusHistory` ORM models per PROJECT_SPEC §5.
- `backend/app/main.py`: FastAPI app, CORS from `settings.allowed_origins_list`, lifespan hook calling `Base.metadata.create_all`, `GET /health` → `{"status":"ok","db":"ok"}` (checks DB with `SELECT 1`).
- `backend/requirements.txt` pinned to exact resolved versions (see root-cause fix below for the `bcrypt` pin).
- Created native Windows venv (`py -3.14 -m venv .venv`) — see root-cause fix #1.

**Root cause fixes:**
1. **Bug:** `python -m venv` under the MSYS2 UCRT64 Python produced a POSIX-style venv (`bin/` not `Scripts/`), which breaks the PowerShell/Git-Bash activation commands CLAUDE.md §3.3 documents as the team standard. **Cause:** MSYS2's Python build targets a POSIX layout regardless of running on Windows. **Fix:** recreated the venv with the native Windows Python (`py -3.14 -m venv .venv`, from the `py` launcher, not the MSYS2 python on PATH). Verified `.venv/Scripts/` exists.
2. **Bug:** `passlib.context.CryptContext(schemes=["bcrypt"]).hash(...)` raised `AttributeError: module 'bcrypt' has no attribute '__about__'` then a downstream `ValueError`. **Cause:** `passlib==1.7.4` (unmaintained since 2020) probes `bcrypt.__about__.__version__` to pick its backend; `bcrypt>=4.1` removed the `__about__` submodule. **Fix:** pinned `bcrypt==4.0.1` (last release with `__about__`) in `requirements.txt`, with a comment explaining why. Verified: hash + verify round-trip succeeds.
3. **Bug:** `uvicorn` failed at startup with `sqlite3.OperationalError: index ix_reports_category already exists`. **Cause:** `models.py` declared `index=True` on the `category`/`status`/`is_duplicate_of` columns *and* duplicated the same index names in an explicit `__table_args__` tuple — SQLAlchemy tried to `CREATE INDEX` each one twice in the same `create_all()` call. **Fix:** removed the redundant `__table_args__` block, kept column-level `index=True`. Verified: clean boot, `/health` → 200, and a second clean restart against the existing DB file (idempotency of `create_all`) also boots clean.

**Assumptions:** none new.

**Known Issues:** none.

**Next:** frontend skeleton (Vite + React + TS + Tailwind), then verify full P0 gate and commit.

---

## 2026-08-13 — P0: frontend skeleton

**Done:**
- Scaffolded `frontend/` with `npm create vite@latest . -- --template react-ts`, installed `react-router-dom`, `axios`, `react-leaflet`/`leaflet` (+`@types/leaflet`) up front since PROJECT_SPEC needs them in P1/P4 and pinning now avoids a second resolution pass.
- `src/api/client.ts`: single axios instance, base URL from `VITE_API_BASE_URL`, throws at import time if unset (PROJECT_SPEC §8 "one API client" rule).
- Replaced the default Vite template `App.tsx`/`App.css`/template assets with a minimal CivicLens placeholder page (h1 + tagline), per P0 scope (placeholder only — real pages come in later phases).
- `frontend/.env.example` (public var template) and `frontend/.env` (gitignored, local dev value) — verified both `frontend/.env` and `frontend/node_modules` are git-ignored via `git check-ignore -v`.

**Root cause fixes:**
1. **Bug:** `npm run build` crashed with `Cannot find native binding ... @rolldown/binding-win32-x64-gnu`. **Cause:** `create-vite@9.1.2` (latest) installed mainline `vite@8.2.0`, which now ships Rolldown (a Rust bundler) as its default, and its native-binding platform resolution picked the wrong target (`win32-x64-gnu`) instead of the installed `win32-x64-msvc` binding on this machine. **Reproduced** under both Git Bash and native PowerShell (ruled out `MSYSTEM`/shell-env as the cause). A clean `node_modules`/`package-lock.json` reinstall did not fix it. **Fix:** pinned `vite@^6` (last stable Rollup-based major, no Rust bundler) + matching `@vitejs/plugin-react@^4`. This is a version-discipline call, not a workaround: Vite 8's rolldown default is new enough on this machine's Node 24.14 that it isn't reliably usable here.
2. **Bug (found immediately after fix #1):** `vite build` then crashed with a Rust panic: `Node-API symbol has not been loaded` (napi-sys). **Isolation:** `tsc -b` alone succeeded (exit 0); `vite build` alone failed; removing the `@tailwindcss/vite` plugin from `vite.config.ts` made the same `vite build` succeed cleanly. **Root cause:** Tailwind v4's `@tailwindcss/vite` plugin depends on `@tailwindcss/oxide` (Rust/napi native addon), which is incompatible with Node v24.14.0 in this environment. **Fix:** downgraded to Tailwind **v3.4.19** (pure JS + PostCSS, no native addon) — `tailwind.config.js` (`content` globs added), `postcss.config.js` (both via `npx tailwindcss init -p`), `src/index.css` uses `@tailwind base/components/utilities`. Verified: built CSS output actually contains the utility classes used in `App.tsx` (`flex`, `min-h-screen`) — Tailwind is genuinely processing, not just passing through.

**Assumptions:**
- Deviated from the letter of PROJECT_SPEC §2 ("React 18 + Vite + TypeScript + TailwindCSS") only on exact major versions: Vite pinned to 6.x (not whatever `latest` resolves to) and Tailwind pinned to 3.x (not 4.x) — both due to native-addon incompatibility with the installed Node v24.14.0, not a design choice. Flagging per CLAUDE.md §3.2 version-discipline rule. React itself is 19.x (installed via create-vite), which satisfies "React 18+".

**Known Issues:** none blocking. Node v24.14.0 is very new (non-LTS-yet) — if the team hits further native-addon breakage in later phases (e.g. an npm package with a Rust/native binary), the pattern to check first is "does a pure-JS/older-major alternative exist" before spending more than 3 attempts on it.

**Next:** run full P0 verification gate (backend boot + `/health`, frontend build, secret scan) and commit.

---

## 2026-08-13 — P1: vertical slice backend (POST/GET /reports)

**Done:**
- `backend/app/schemas.py`: `ReportOut`, `ReportCreateResponse`, `ReportDetailOut`, `StatusHistoryOut` — Pydantic v2, `from_attributes=True` for ORM conversion. No raw dicts cross the API boundary.
- `backend/app/storage.py`: `save_report_image()` — validates `content_type` against the allowlist, caps size at `MAX_UPLOAD_MB`, and verifies the bytes are actually a decodable JPEG/PNG/WEBP via Pillow (`Image.open(...).verify()`) rather than trusting the client's declared MIME type. Saves under a `uuid4` filename; the original client filename is never used for anything (path-traversal-proof by construction). Tested directly: a real JPEG round-trips; a shell script with a spoofed `image/jpeg` content-type is correctly rejected with 415.
- `backend/app/routers/reports.py`: `POST /reports` (multipart) and `GET /reports` (status/category/min_priority/bbox filters, `sort=priority|recent`, excludes duplicates by default). AI is `# STUB:` (fixed `category="pothole", confidence=0.5, severity=3`, zero embedding) — the real pipeline lands in P2.
- `backend/app/main.py`: mounted `/uploads` as `StaticFiles`, included the reports router under `/api/v1`.

**Root cause fixes:** none this unit (storage.py's negative-case test above caught the intended behavior correctly on the first pass — no bug).

**Assumptions:**
- **P1 has no auth system yet** (auth is explicitly a P4 milestone item: "JWT auth enforced"). PROJECT_SPEC §6's API contract table doesn't mark `POST /reports` as requiring auth (unlike `GET /reports/mine` and `PATCH .../status`, which are explicitly marked). Since `reports.user_id` is a frozen NOT NULL FK, `_get_demo_user()` seeds/reuses one `demo@civiclens.local` citizen row and attributes all P1 submissions to it. This is a real DB row, not fabricated data — flagged here per CLAUDE.md §0.5. **This will need revisiting in P4**: once real auth exists, `POST /reports` should attach the authenticated user if a valid token is present, and the demo-user fallback can stay for anonymous/no-login submission (the contract doesn't require login to report).

**Verification (manual, via curl against a running server):**
- `POST /api/v1/reports` with a real JPEG + lat/lng/description/address → 201, correct `priority_score` (46.0, matches the §4 formula by hand-calculation), image byte-verified and saved.
- `GET /api/v1/reports`, `?sort=recent&limit=1`, `?category=pothole`, `?bbox=28,77,29,78` → all correct results.
- `GET /api/v1/reports?category=not_a_category` → 422 as expected.
- `POST /api/v1/reports` missing the required `image` field → 422 as expected.
- Uploaded image fetched back via `GET /uploads/<uuid>.jpg` → 200, `content-type: image/jpeg`.
- Cleaned up all test DB/upload artifacts after verification.

**Known Issues:** none blocking.

**Next:** citizen submit form (frontend) wired to `POST /reports`, then a reports list view to prove the full loop, closing out P1.

---

## 2026-08-13 — P1: citizen submit form + browser-verified end-to-end

**Done:**
- `frontend/src/types.ts`: `ReportOut`/`ReportCreateResponse` mirroring the backend Pydantic schemas.
- `frontend/src/api/reports.ts`: `createReport()` (multipart) and `listReports()`, both through the shared `apiClient`.
- `frontend/src/pages/Report.tsx`: citizen submit form — photo input (`capture="environment"` for mobile camera), `navigator.geolocation` with a manual lat/lng fallback when permission is denied or unsupported, optional address/description, loading state on submit, inline error messages, and a result card (category/severity/priority, "merged with report #N" path wired for when dedup lands in P3).
- `frontend/src/App.tsx`: renders `Report` as the app's current entry view (no router yet — added when `/track`/`/dashboard`/`/map` exist in later phases, per scope discipline).

**Root cause fixes:**
1. **Bug (caught by CLAUDE.md's mandatory browser check, not by build/typecheck):** submitted a real report through an actual headless-Chromium session (Playwright, since `chromium-cli` wasn't installed — installed Playwright + Chromium in the scratchpad as the documented fallback) — the result card showed a broken-image icon instead of the uploaded photo. **Isolation:** `console --errors` was empty, `tsc`/`vite build` were clean — this was a runtime-only bug invisible to every non-browser check. **Root cause:** `report.image_url` from the backend is root-relative (`/uploads/x.jpg`); the `<img>` tag resolved it against the *frontend's* origin (`localhost:5173`) instead of the backend's (`localhost:8000`) — a 404. This isn't dev-only: PROJECT_SPEC's deploy targets (frontend on Vercel/Netlify, backend on Render/Railway) put them on different origins in production too. **Fix:** added `resolveImageUrl()` in `api/client.ts`, deriving the API origin from `VITE_API_BASE_URL` via `new URL(...).origin` and prefixing image paths with it. **Verified by re-running the exact same Playwright script**: the actual uploaded photo (a solid-blue test JPEG) now renders in the result card, confirmed by screenshot.

**Verification (real browser, Playwright against the live dev servers — not just curl/build):**
- Screenshots: filled form → submit → result card, all captured and visually inspected.
- Result card text after submit: `Category: pothole`, `Severity: 3/5`, `Priority score: 46` — matches the backend response and the hand-verified formula.
- `console --errors` equivalent (page `console`/`pageerror` listeners): zero errors, both before and after the image-URL fix.
- Cleaned up: killed both dev servers, removed `backend/uploads/` and `backend/civiclens.db` test artifacts, scratchpad Playwright project is outside the repo (never touched git).

**Assumptions:** none new (see prior entry re: demo user).

**Known Issues:** none blocking. `listReports()` exists in `api/reports.ts` but has no consuming UI yet — a live "shows in list" view is the authority Dashboard (P3) and citizen Track view (P4); the P1 gate ("shows in list") is satisfied via the verified `GET /reports` API response for now.

**P1 vertical slice complete: submit → AI (stubbed) → stored with priority → retrievable, browser-verified end to end.**

**Next:** P2 — wire the real AI pipeline (`ai/pipeline.py`: CLIP zero-shot classification, severity heuristic, embeddings) into `POST /reports`, replacing the stub.

---

## 2026-08-13 — P2: AI online (CLIP classification, severity, embeddings)

**Done:**
- Verified `torch`/`torchvision`/`open_clip_torch` actually install and work on this Python 3.14 (native Windows) setup before writing any code against them — real risk given how new 3.14 is. `torch==2.13.0+cpu` has a native `cp314-win_amd64` wheel; `open_clip_torch==3.3.0` installs cleanly on top. Verified the exact `open_clip.create_model_and_transforms`/`get_tokenizer` signatures via `inspect.signature` on the installed version rather than assuming from memory (CLAUDE.md §3.2).
- `ai/embeddings.py`: CLIP `ViT-B-32`/`laion2b_s34b_b79k` singleton (lazy-loaded once, `warm_up()` forces it at app startup instead of on the first request), `encode_image()`/`encode_text()` returning float32 L2-normalized vectors. `EMBEDDING_DIM = 512` is a static constant (not derived from the model) specifically so the failure-fallback path never has to touch the model to build a zero vector.
- `ai/classifier.py`: zero-shot classification — one natural-language prompt per category (10 of the 11 `CATEGORIES`; `other` is the fallback, not a prompted class), softmax over cosine similarities scaled by the conventional CLIP logit scale (100), `confidence < 0.25` → `category="other"`. Threshold branch logic verified in isolation with a controlled tiny text-feature matrix (real CLIP embeddings can't reliably be forced into a "uniform" case, so the fallback path was tested with a synthetic 5-orthogonal-category setup instead — same code path, deterministic input).
- `ai/severity.py`: heuristic 1-5 estimate combining `CATEGORY_CRITICALITY` (imported from `app.scoring`, not duplicated — CLAUDE.md §3.1), an edge-density "affected area" proxy (PIL `FIND_EDGES` on grayscale), and a confidence blend that pulls the result toward the neutral midpoint (3) when confidence is low. **Deliberately excludes** the spec's 4th signal ("duplicate count"): `analyze_image()`'s frozen signature has no report-count input, and per PROJECT_SPEC §1's flow diagram, severity is computed *before* the dedup check runs — documented in the module docstring rather than silently dropped.
- `ai/pipeline.py`: `analyze_image()`, the sole entry point. Never raises — catches `UnidentifiedImageError`/`OSError`/`ValueError`/`RuntimeError` and returns the fallback (`category="other", confidence=0.0, severity=3, embedding=zeros`). Also short-circuits to the same fallback when `settings.ai_enabled` is `False`.
- Wired into `backend/app/routers/reports.py`: real `analyze_image()` call (via `run_in_threadpool`, since CLIP inference is synchronous/CPU-bound and would otherwise block the event loop inside the `async def` endpoint), real embedding persisted to `report_embeddings`. `backend/app/main.py` lifespan now calls `ai.embeddings.warm_up()` at startup when AI is enabled, wrapped in try/except so a warm-up failure degrades to per-request fallback instead of crashing boot.

**Root cause fixes / design decisions:**
1. **Cross-package import:** `ai/` is a sibling of `backend/` at the repo root (per PROJECT_SPEC §3), not a backend subpackage, so `from ai.pipeline import analyze_image` doesn't resolve from backend's own cwd. Fixed with a `sys.path` bootstrap in `backend/app/__init__.py` (runs once, automatically, before any `app.*` submodule) rather than requiring `PYTHONPATH` to be set manually — the latter is easy to forget and would silently break the "uvicorn boots clean" gate in a fresh shell.
2. **CLAUDE.md vs PROJECT_SPEC fallback-category wording conflict:** CLAUDE.md §4 describes the AI failure fallback using `category="unclassified"`; PROJECT_SPEC §7's literal contract for `analyze_image()` says `category="other"`, and `"unclassified"` isn't a member of the frozen `CATEGORIES` list at all. Resolved in favor of PROJECT_SPEC (`"other"`), per CLAUDE.md's own preamble naming PROJECT_SPEC as authoritative for schema/contract values — documented in `ai/pipeline.py`'s module docstring rather than silently picking one. Not treated as a hard-stop conflict since it's a wording mismatch in prose, not a genuine architectural disagreement.

**Verification (real, on this machine — no mocked AI output presented as real):**
- Happy path: real image → non-zero, L2-normalized 512-dim embedding persisted to `report_embeddings` (checked directly via sqlite3, not just trusting the response body).
- Failure fallback (corrupt file, nonexistent file): `analyze_image()` returns the exact documented fallback in both cases, confirmed never raises.
- **P2 gate — "kill the model deliberately, confirm submissions still succeed":** booted with `AI_ENABLED=false`; `POST /reports` still returned `201` with `category="other", ai_confidence=0.0, severity=3`.
- **P2 gate — 3 real photos, categories + priority scores** (synthetic test images — no real civic photos available in this environment, flagged explicitly since PROJECT_SPEC's own gate language says "real photo"):
  - Solid blue square → `illegal_dumping`, confidence 0.302, severity 3, priority 41.0
  - Gray field with a dark irregular ellipse (built to visually resemble a pothole) → **`pothole`, confidence 0.958**, severity 3, priority 46.0 — strong evidence the zero-shot classifier is doing genuine semantic matching, not returning noise
  - Multi-colored cluttered scene → `illegal_dumping`, confidence 0.340, severity 3, priority 41.0
- Cleaned up all test DB/upload artifacts after each verification pass.

**Assumptions:** none new beyond the fallback-category resolution above.

**Known Issues:** classification was only verified against synthetic test images (no real pothole/garbage/streetlight photos on hand in this environment) — the pothole-lookalike result (95.8% confidence) is a strong positive signal, but real-world accuracy on genuine field photos is not independently confirmed here. Model weights download from HuggingFace Hub on first run (~600MB, cached afterward at `~/.cache/huggingface`) — first boot on a fresh machine (or fresh deploy target) will be slow; `warm_up()` at least keeps that cost at startup instead of on a user's first request.

**P2 complete: real CLIP classification + severity + embeddings live in `POST /reports`, AI-failure degradation verified.**

**Next:** P3 — real duplicate detection (geo+time SQL pre-filter, then cosine similarity on the small candidate set) and the authority dashboard UI.

---

## 2026-08-13 — P3: duplicate detection, merge logic, status/history, authority dashboard

**Done:**
- `backend/app/geo.py`: `haversine_distance_meters()`, verified against known geometric distances (0m same-point, ~50m offset, 1° longitude at a given latitude) — not just unit-tested against itself.
- `ai/dedup.py`: `cosine_similarity()`/`find_best_match()` — pure math, no DB access, tested in isolation.
- `backend/app/dedup.py`: `find_duplicate_canonical()` — the 3-gate orchestration (geo bbox pre-filter → exact haversine ≤100m → category match → time window ≤30d → cosine similarity ≥0.86, checked only against the small surviving candidate set). Each gate tested **independently** against a real SQLite session (geo, category, visual, and time all verified to correctly reject on their own, not just pass when everything lines up).
- Wired into `POST /reports`: on match, the new report gets `is_duplicate_of` set, the canonical's `report_count` increments and `priority_score` recomputes.
- `GET /reports/{id}` (with `duplicates[]` and `status_history[]`) and `PATCH /reports/{id}/status` (writes `status_history`, validates against `STATUSES`) — both tested via real HTTP calls (valid update, invalid status → 422, 404 on missing report).
- `GET /dashboard/stats` — `total`, `by_status`, `by_category`, `avg_resolution_hours`, `high_priority_count`, all canonical-only. Verified against real seeded data with a mix of statuses/categories and one resolved report.
- Frontend: `Dashboard.tsx` (stat cards, status/category/min-priority filters, inline status-update dropdown per report), routing added (`App.tsx` now has `/` → Report, `/dashboard` → Dashboard, since there are two real pages now).

**Root cause fixes:**
1. **Bug caught before it ever ran against the live endpoint:** `datetime.now(timezone.utc) - canonical.created_at` would have raised `TypeError: can't subtract offset-naive and offset-aware datetimes` the moment a duplicate merge happened. **Cause:** SQLAlchemy's SQLite `DateTime` column drops tzinfo on read — `created_at` is always written as UTC (`_utcnow()`), but comes back as a naive datetime object. Verified this directly (`u.created_at.tzinfo` → `None`) before writing the fix, not assumed. **Fix:** `models.py` gained `as_utc()`, re-attaching `timezone.utc` to naive values before any Python-side arithmetic. SQL-side comparisons (`WHERE created_at >= cutoff`) were *not* affected — confirmed separately, since SQLAlchemy's bind-parameter conversion is consistent regardless of which side of the query holds the datetime.
2. **Process mistake, not a code bug:** committed `geo.py` directly to `main` — forgot to branch before starting P3. Caught immediately via `git branch --show-current`. Fixed by creating `feat/p3-dedup-dashboard` at that commit, then `git reset --hard HEAD~1` on `main` to restore it to the P2 merge point. Commit was preserved on the new branch; nothing lost, `main` never had a stray commit pushed anywhere.

**Concurrent session note:** the user ran a second Claude/Antigravity session directly in this same working directory (not the isolated worktree set up for the parallel map-view session) that substantially reworked `ai/classifier.py`, `ai/dedup.py`, `ai/embeddings.py`, `ai/pipeline.py`, `ai/severity.py`, and added `ai/constants.py` + a full `ai/tests/` pytest suite + `ai/samples/`. Before building anything further on top of it: re-ran the full regression suite this session already relies on — real HTTP submit → classify → embed → dedup-merge flow, and the `AI_ENABLED=false` fallback — all identical results to before the external changes, so `analyze_image()`'s contract held. Did **not** edit the reworked `ai/` files further (that module now has active concurrent work happening in it) beyond verifying compatibility.
- **Known issue introduced by that work, not fixed here:** `ai/constants.py` duplicates `backend/app/scoring.py`'s frozen values (CATEGORIES, weights, thresholds) so `ai/` tests can run standalone without backend on the path — this is exactly the duplication CLAUDE.md §3.1 says not to have. Real tension between "one source of truth" and "ai/ must be standalone-testable"; needs a team decision (e.g. backend imports from `ai/constants.py` instead of the reverse, or `ai/` tests get a conftest shim) rather than a unilateral fix mid-flight on someone else's in-progress module.
- **Known issue, not fixed here:** `ai/tests/test_dedup.py::test_3gate_duplicate_all_pass` is flaky — uses unseeded `np.random.randn` noise that can occasionally push cosine similarity below the 0.86 threshold. Not touched, since it's in a test file that may be under active edit in the concurrent session.

**Verification (real, via the actual HTTP API):**
- **P3 core gate — "two similar photos 50m apart → one canonical entry with report_count=2":** submitted the same test image at (28.4595, 77.0266) then (28.45995, 77.0266) — report 2 came back `is_duplicate_of: 1`, and `GET /reports` showed report 1 with `report_count: 2`, `priority_score` correctly recomputed 46.0 → 48.0. `GET /reports?include_duplicates=true` correctly showed both.
- Adjacent case: a genuinely different photo far away still created its own canonical entry (no false-positive merging).
- `GET /reports/{id}` detail correctly listed the duplicate under `duplicates[]`.
- `PATCH .../status` correctly updated status, wrote history, rejected an invalid status with 422, 404'd on a missing report.
- Dashboard browser-verified with Playwright against live seeded data: stats cards, category filter, and a live status-update click all worked with zero console errors (screenshots captured). Regression-checked `/` (the Report page) still renders correctly after adding routing.

**Assumptions:**
- `PATCH /reports/{id}/status` has **no role check yet** — PROJECT_SPEC §6 marks it "Authority role only," but no auth system exists before P4 (same reasoning as the P1 demo-user note). Documented inline in the endpoint; anyone can call it until P4.

**P3 complete: real dedup/merge verified end to end, authority dashboard live and browser-tested.**

**Next:** P4 — Leaflet map (being built in parallel by a second session in an isolated worktree, `feat/p4-map-view`, frontend-only), citizen `/track` view, JWT auth + role gating (including finally locking down `PATCH .../status`).

---

## 2026-08-13 — P4: JWT auth, role gating, citizen tracking

**Done:**
- `backend/app/auth.py`: `hash_password`/`verify_password` (bcrypt via passlib), `create_access_token`/`_decode_token` (JWT, HS256), `get_current_user` (401 if missing/invalid/expired token), `get_current_user_optional` (returns `None` instead of raising — verified `OAuth2PasswordBearer(auto_error=False)` actually does this before relying on it), `require_authority` (403 if role != "authority").
- `backend/app/routers/auth.py`: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`. Login returns the same generic "Incorrect email or password" for both a wrong password and a nonexistent email — deliberate, avoids user enumeration.
- `POST /reports` now attaches the real authenticated user when a valid token is present, falls back to the P1 demo user for anonymous submissions (PROJECT_SPEC §6 doesn't mark this endpoint as requiring auth, so anonymous reporting stays allowed).
- `PATCH /reports/{id}/status` now requires `require_authority` — closes the gap flagged since P1/P3. `changed_by` is recorded on `status_history` (confirmed via direct DB query — not currently surfaced in the API response schema, a deliberate minimal-exposure choice).
- `GET /reports/mine` (auth required) added.
- Frontend: `auth/AuthContext.tsx` (login/register/logout, session in `localStorage`), an axios request interceptor in `api/client.ts` that attaches the bearer token automatically, `Login.tsx`, `Track.tsx` (citizen's own reports), `Dashboard.tsx` now gated to `role === "authority"` (shows a login prompt otherwise, matching PROJECT_SPEC §8 "Authority-only").

**Root cause fixes:**
1. **Process mistake, caught and fixed twice:** a concurrent Claude/Antigravity session the user ran directly in this same working directory (not the isolated worktree set up for the map-view session) was independently staging its own changes to `ai/tests/test_dedup.py`. Because both sessions share one `.git/index`, plain `git add <file> && git commit` had a race window — the other session's `git add` landed in between and got swept into two of my commits under my commit message. Caught both times by checking `git show --stat HEAD` immediately after committing. **Fix, applied going forward:** `git commit -m "..." -- <exact path>` instead of `git add` + bare `git commit` — this stages+commits only the given pathspec regardless of whatever else is sitting in the shared index, so it's race-proof. Recovery when it happened: `git reset --soft HEAD~1 && git restore --staged <swept-file>` — puts the swept file's edits back in the working tree, untouched and uncommitted, so the other session's work isn't lost or misattributed.
2. Verified (not assumed) `EmailStr` needs the optional `email-validator` package — hit `ImportError` immediately on first use, installed and pinned `email-validator==2.3.0`.
3. `.local` email domains (like the P1 demo user's `demo@civiclens.local`) are correctly rejected by `EmailStr` as a reserved TLD — not a bug, just meant using realistic-looking test emails for the auth flow. The demo user itself is unaffected since `_get_demo_user` constructs the ORM `User` directly, bypassing Pydantic email validation.

**Verification (real, via HTTP API and then a full real-browser pass):**
- API-level: register (citizen + authority), duplicate-email 409, login (correct/wrong-password/nonexistent-all paths, generic error), `/auth/me` (valid/missing/garbage token), anonymous vs. authenticated `POST /reports` (correct `user_id` attribution both ways), `GET /reports/mine` scoped correctly, `PATCH .../status` — 401 no token, 403 citizen token, 200 authority token.
- Browser (Playwright, headless Chromium): dashboard locked when logged out → register as authority → dashboard unlocks and loads live stats → log out → dashboard re-locks → register as a separate citizen account → submit a real report while logged in → `/track` shows it. Zero console errors throughout. Screenshots captured (one attached above — nav bar correctly shows "Log out (City Admin)").

**Assumptions:** none new.

**Known Issues:** none blocking. Parallel map-view session (`feat/p4-map-view` worktree) has not committed yet as of this entry — will merge once it lands.

**P4 complete: full JWT auth, role gating, citizen tracking, browser-verified end to end.**

**Next:** merge the map-view branch when ready, then P5 (hardening: error/loading state audit, input validation pass, seed data, README) and P6 (deploy prep, final secret scan).

---

## 2026-08-13 — P5: hardening (validation, seed data, README, AI-degradation gate)

**Done:**
- Error/loading state audit: all four async frontend pages (`Report.tsx`, `Dashboard.tsx`, `Track.tsx`, `Login.tsx`) already had loading/error states built in as they were written in P1/P3/P4 — confirmed by grep, no gaps found.
- Input validation: `POST /reports`'s `description`/`address` form fields had no length cap (SQLite doesn't enforce `String(255)` at the DB level — it's advisory only), so an unbounded string could be submitted. Added `max_length=2000`/`255` on the Pydantic `Form(...)` fields, verified a 2500-char description gets 422'd and a normal one still succeeds.
- `backend/seed.py`: seeds 18 demo reports across real Gurugram-area coordinates, spanning all 5 statuses and a real spread of priority bands (42-84 in the actual run). **Every category/severity/embedding comes from a genuine `analyze_image()` run** against real sample photos (`ai/samples/*.jpg`, added by the concurrent ai/ session) — nothing hardcoded, per CLAUDE.md §0.5. Only submission metadata (location jitter, timestamp, status, report_count) is synthetic, which is exactly what PROJECT_SPEC §9 asks P5 to pre-seed. Every seed report's description is prefixed `[SEED DATA]` so it's never mistaken for genuine citizen activity. Idempotent (skips if reports already exist, `--force` to override). Sample images get copied into `settings.upload_dir/seed/` so they're actually servable via the existing `/uploads` mount (`ai/samples/` itself isn't on that mount).
- `README.md`: setup (PowerShell + Git Bash variants, per CLAUDE.md §3.3), demo flow, AI-degradation instructions, page/route table.

**Root cause fixes:**
1. Seed script's `avg_resolution_hours` came out as `0.0` for all resolved reports — cause: `created_at` and `updated_at` were both set to the same seeded timestamp. Fixed by giving `resolved`-status seed reports a randomized 2-72h gap between the two, matching how a real resolution would look. Verified: `41.1` after the fix.

**Verification (real):**
- `python seed.py` run for real: 18 reports created, real AI categories logged to console (`pothole`, `garbage_dump`, `waterlogging` — matching the sample filenames semantically, confirming genuine classification, not random output). Re-run confirmed idempotency (skipped without `--force`).
- `GET /dashboard/stats` against the seeded data: `total: 18`, all 5 statuses represented, 3 categories, `high_priority_count: 3`, `avg_resolution_hours: 41.1`.
- Seed images confirmed servable: `GET /uploads/seed/waterlogging.jpg` → 200, `image/jpeg`.
- **Real browser** (Playwright): logged in as a newly-registered authority, dashboard rendered all 18 seeded reports with real thumbnails, correct priority badges, sorted by priority — screenshot captured, zero console errors.
- **P5 gate — "kill the AI module, submissions still work end to end," done as a full browser pass this time (not just curl):** booted with `AI_ENABLED=false`, drove the citizen submit form in a real headless browser — result card correctly showed `Category: other, Severity: 3/5, Priority score: 36`, zero console errors.

**Assumptions:** none new.

**Known Issues:** none blocking.

**P5 complete.**

**Next:** P6 — deploy config, final secret scan, merge the map-view branch whenever it lands.

---

## 2026-08-14 — P4 (completing): MapView, and reconciling the parallel-session worktrees

**Context:** the parallel-session map-view worktree (`E:/GitHub/Hack-4-Crown-map`, branch `feat/p4-map-view`) never received a commit despite hours of this session's own progress through P3-P5. Asked the user how to proceed; they asked me to build it directly. Discovered in the process a **third** piece of unmerged work: `E:/GitHub/Hack-4-Crown-frontend` (branch `feat/frontend-core`) — one commit independently building Report/Track/Dashboard pages + minimal JWT auth, branched from the P2 merge point, diverged from and overlapping with the (already-merged, browser-tested) P3/P4 work in this session. **Left it completely untouched** — not mine to merge, reconcile, or delete; it may be someone's in-progress work. Removed only the empty `feat/p4-map-view` worktree/branch I had created myself for this exact purpose, and rebuilt it fresh off current `main`.

**Done:**
- `frontend/src/pages/MapView.tsx`: Leaflet map (`react-leaflet` v5, already installed since P0) using `CircleMarker` (SVG-rendered) rather than the default `Marker` — deliberately sidesteps the well-known Leaflet-default-icon-vs-bundler path issue entirely, and gives exact control over the marker color needed for the priority bands anyway. Verified the actual `react-leaflet` v5 type exports (`CircleMarker`, `MapContainer`, `Popup`, `TileLayer`) before writing code, not assumed from memory. Colors: green <40, amber 40-70, red >70 (exact PROJECT_SPEC §8 thresholds). Popup shows the real report thumbnail, category, priority, status, address, and merged-report count. Tile URL reads `VITE_MAP_TILE_URL` (added to both `.env`/`.env.example`) with an OSM default fallback.
- Wired into routing/nav (`/map`, public — not auth-gated, matching PROJECT_SPEC §8's table which doesn't mark it restricted).

**Verification (real browser, Playwright, against live seeded data):**
- 18 real `CircleMarker` elements rendered on real Gurugram map tiles, correctly colored (screenshot confirms actual amber/red fills matching real priority scores, not placeholders).
- Clicked a marker → popup opened with the correct data (`pothole`, `Priority: 59.3`, `Status: Rejected`, `Sector 45, Gurugram`, `3 reports merged`) — matched the seeded DB row exactly.
- First popup screenshot looked like the thumbnail was missing; **did not assume this was fine** — checked `img.naturalWidth` directly (1024, i.e. genuinely loaded) and re-screenshotted with more wait time, confirming it was a screenshot-timing artifact, not a real bug, before moving on.
- Zero console errors throughout.

**Assumptions:** none new.

**Known Issues:** `feat/frontend-core` (a competing, unmerged, unrelated-to-map body of frontend/auth work from a third worktree) still exists and hasn't been reconciled with the already-merged P3/P4 work in `main` — flagging here so the next person (or session) knows it's there and why it wasn't touched.

**All 4 PROJECT_SPEC.md §1 demo success criteria now buildable end to end: submit→classify→priority (✓ P1/P2), duplicate merge (✓ P3), status update reflected to citizen (✓ P3/P4), map colored by priority (✓ this entry).**

**Next:** P6 — deploy config, final secret scan.
