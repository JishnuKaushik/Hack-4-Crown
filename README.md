# CivicLens

Citizens report civic issues (potholes, garbage, broken streetlights, waterlogging...) with a photo and location. A zero-shot CLIP model classifies the issue, estimates severity, and detects duplicate reports of the same physical problem. A priority score ranks everything on an authority dashboard.

See `PROJECT_SPEC.md` for the full architecture/schema/API contract, and `DEVLOG.md` for the build history and root-cause notes.

## Stack

FastAPI + SQLAlchemy 2.x + SQLite (backend), CLIP (`open_clip`, `ViT-B-32`/`laion2b_s34b_b79k`) for zero-shot classification + embeddings, React 19 + Vite + TypeScript + Tailwind v3 (frontend), JWT auth.

## Prerequisites

- Python 3.11+ (developed/verified on 3.14, native Windows build — **use the `py` launcher, not an MSYS2/UCRT64 Python**, or you'll get a POSIX-style venv layout on Windows)
- Node.js 20+
- ~2GB free disk for the CLIP model weights (downloaded once, cached at `~/.cache/huggingface`)

## Backend setup

PowerShell:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .env
# edit .env: set SECRET_KEY to a real generated value (see .env.example for the command)
```

Git Bash:

```bash
cd backend
py -3.14 -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp ../.env.example .env
# edit .env: set SECRET_KEY to a real generated value
```

Generate a real `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Seed demo data (optional but recommended before a demo — 18 reports across Gurugram, real AI classification on real sample photos, spanning all statuses and priority bands):

```bash
python seed.py
```

Run the API:

```bash
uvicorn app.main:app --reload
```

- `GET http://localhost:8000/health` → `{"status":"ok","db":"ok"}`
- Interactive API docs: `http://localhost:8000/docs`

## Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

## Pages

| Route | Who | What |
|---|---|---|
| `/` | Anyone | Report an issue — photo + location (geolocation or manual), submits to `POST /reports` |
| `/track` | Logged-in citizen | Their own submitted reports (`GET /reports/mine`) |
| `/dashboard` | Authority role only | Sorted/filterable report list, stat cards, status updates |
| `/login` | Anyone | Login / register (citizen or authority role) |

## Demo flow

1. Run `python seed.py` (once) so the dashboard/map aren't empty.
2. Register an authority account at `/login` (role dropdown → Authority).
3. Submit a report at `/` with a real photo — watch it appear with a genuine AI-assigned category, severity, and priority score.
4. Submit a near-duplicate (same photo, nearby coordinates) — it merges into the existing report instead of creating a new one (`report_count` increments).
5. View `/dashboard` as the authority — filter, and change a report's status.
6. Log in as a citizen and check `/track` to see status update reflected.

## AI degradation

The AI layer can be disabled without breaking submissions — every AI call has a fallback (`category="other", severity=3, confidence=0.0`) so a report always saves even if the model fails to load or errors on a given image:

```bash
AI_ENABLED=false uvicorn app.main:app --reload
```

## Environment variables

See `.env.example` (backend) and `frontend/.env.example`. Real secrets go in `.env` files (gitignored) or your deploy platform's env-var UI — never committed. Run `bash scripts/check-secrets.sh` before every commit (also installed as the pre-commit hook).
