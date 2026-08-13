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
