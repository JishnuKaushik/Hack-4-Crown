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
