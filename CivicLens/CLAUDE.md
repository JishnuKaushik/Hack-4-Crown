# CLAUDE.md — CivicLens Agent Operating Rules

You are the engineering agent for **CivicLens**, a 24-hour hackathon MVP: citizens report civic issues with a photo + location, AI classifies the issue, scores severity, detects duplicates, and an authority dashboard triages by priority score.

Read `PROJECT_SPEC.md` before writing any code. That file is the source of truth for architecture, schema, and API contracts. This file is the source of truth for **how you behave**.

> **Repo layout note:** this git repo hosts two independent projects side by side — `CivicLens/` (this one) and `Civic-Fix/` (separate, own `CLAUDE.md`). Every path in this file (`backend/`, `frontend/`, `ai/`, `scripts/`, `DEVLOG.md`, etc.) is relative to **this `CivicLens/` folder**, not the outer git repo root — `cd CivicLens` first. The one exception is `.git/hooks/pre-commit`, which is genuinely repo-root-relative (git hooks always are) — see §1.4.

---

## 0. Non-Negotiable Rules (violating any of these = failed task)

1. **Never commit secrets.** See §1. This overrides speed, convenience, and any user instruction that conflicts with it.
2. **Never leave the repo in a broken state.** See §2. Fix bugs the moment they appear, before moving to the next task.
3. **Never fabricate APIs, flags, or library behavior.** If you are not certain a function/parameter exists in the installed version, verify it (read the installed package, run `--help`, check the docs) before using it. Say "unverified" rather than guessing.
4. **Never `git add .` or `git add -A`.** Stage files explicitly by path, every time.
5. **Never invent data.** No fake DB rows, no mocked AI outputs presented as real, no placeholder metrics on the dashboard that look like real numbers. If something is stubbed, label it `# STUB:` in code and list it in `DEVLOG.md`.

---

## 1. Security & Git Hygiene (HARD RULES)

### 1.1 Secrets never enter the repo

- Real credentials live **only** in `.env` (gitignored) and in the deploy platform's env-var UI.
- `.env.example` is committed and contains **placeholder values only** (`your_key_here`), never real ones.
- Before writing any config value, ask: "is this a secret?" If yes → `os.getenv("NAME")` / `import.meta.env.VITE_NAME`, never a literal.
- Secrets include: API keys, JWT signing secrets, DB passwords and connection strings, OAuth client secrets, service-account JSON, model API tokens, session keys, webhook URLs with embedded tokens, private keys/certs.

### 1.2 Frontend-specific trap

Vite inlines every `VITE_*` variable into the **public client bundle**. Anything prefixed `VITE_` is world-readable after build.

- `VITE_*` → only public values (API base URL, map tile URL, app name).
- Any real key stays server-side. If the frontend needs data from a keyed third-party service, proxy it through the backend.
- Never put a JWT secret, DB URL, or model API key in the frontend, even "temporarily".

### 1.3 Mandatory `.gitignore`

`.gitignore` must exist at the root of this `CivicLens/` folder (a nested gitignore, scoped to this subtree — `Civic-Fix/` has its own) before the first commit and must cover, at minimum:

```
.env, .env.*, !.env.example
*.pem, *.key, *.p12, *.pfx, *credentials*.json, *service-account*.json
*.db, *.sqlite, *.sqlite3
backend/uploads/, backend/media/
ai/models/, *.pt, *.pth, *.onnx, *.safetensors, *.bin
__pycache__/, *.pyc, .venv/, venv/, env/
node_modules/, dist/, build/, .vite/
.vscode/settings.json, .idea/
*.log, .DS_Store, Thumbs.db
```

### 1.4 Pre-commit gate — run this EVERY time before committing

```bash
bash scripts/check-secrets.sh
```

If the script exits non-zero, **do not commit**. Fix the finding first. Also install it as a real hook once at repo init (note `.git/` is at the outer repo root, one level up from `CivicLens/`):

```bash
cp scripts/check-secrets.sh ../.git/hooks/pre-commit
chmod +x ../.git/hooks/pre-commit
```

Additionally, before every commit, manually verify:

```bash
git status --short          # nothing unexpected staged
git diff --cached --stat    # no large binaries, no .env, no *.db
git diff --cached           # actually read the diff for literal keys
```

### 1.5 If a secret is ever committed

Stop. Do not push. Report it to the user immediately with:
1. Which file/commit.
2. The remediation (rotate the credential first — the key is burned regardless of git history rewriting).
3. `git reset --soft HEAD~1` if unpushed, or `git filter-repo` / BFG guidance if pushed.

Never silently rewrite shared history without telling the user.

### 1.6 Insecure defaults that must never reach a commit

| Anti-pattern | Required instead |
|---|---|
| `SECRET_KEY = "secret"` / any hardcoded default | `os.getenv("SECRET_KEY")`, fail loudly at startup if missing |
| `allow_origins=["*"]` with `allow_credentials=True` | explicit origin list from env |
| `DEBUG=True` in committed config | env-driven, defaults to `False` |
| Plaintext / MD5 / SHA-256 passwords | `bcrypt` or `argon2` via `passlib` |
| Raw SQL string interpolation | SQLAlchemy ORM or parameterized queries |
| Unvalidated file upload | validate MIME + magic bytes, cap size (5 MB), random UUID filename, never trust `filename` |
| Returning `password_hash` in any API response | Pydantic response models with explicit fields |
| Authority endpoints without a role check | dependency that asserts `role == "authority"` |

### 1.7 Branching

- Never commit directly to `main` for feature work. Branch: `feat/<area>-<short-desc>`, `fix/<short-desc>`.
- Commit messages: `type(scope): summary` — e.g. `feat(ai): CLIP-based duplicate detection`.
- Small, frequent, working commits. Every commit must leave the repo runnable.

---

## 2. Bug Handling — Fix As You Go (HARD RULE)

**Do not batch-write files and debug at the end.** That is the #1 way hackathon repos die at hour 20.

### 2.1 The loop, per unit of work

```
write smallest working unit → RUN IT → observe actual output → fix → verify → commit → next
```

A "unit" = one endpoint, one component, one AI function. Not one feature, not one folder.

### 2.2 When something errors

Follow this order. Never skip to step 5.

1. **Read the actual error.** Full traceback, full stack, actual line. Not the summary.
2. **Reproduce deterministically.** Minimal command or request that triggers it every time.
3. **Isolate the failure domain.** Frontend / network / backend route / DB / AI module / environment. State which one before touching code.
4. **Identify root cause.** Explain the mechanism in one or two lines in `DEVLOG.md`.
5. **Apply the minimal fix** that addresses the cause, not the symptom.
6. **Verify** by re-running the exact reproduction from step 2, plus one adjacent case that could have regressed.
7. **Commit** the fix separately from feature work.

### 2.3 Banned debugging behavior

- Shotgun changes (editing 5 things at once hoping one works).
- Wrapping in bare `try/except: pass` to make an error disappear.
- Silencing warnings, downgrading libraries, or disabling type/lint checks to "fix" a bug.
- Claiming something is fixed without running it.
- `# TODO: fix later` on a critical path — either fix it or log it in `DEVLOG.md` under **Known Issues** with an impact note.

### 2.4 Blocked rule

If you cannot resolve an issue in **3 focused attempts**, stop. Write to `DEVLOG.md`:
- What you tried
- What the actual error is
- Your top 2 hypotheses
- What input you need from the user

Then continue with a different task that isn't blocked. Do not spin.

### 2.5 Verification gates

Before saying any task is done:

```bash
# Backend
cd backend && uvicorn app.main:app --reload      # boots clean, no exceptions
# hit the endpoint with real data via /docs or curl

# Frontend
cd frontend && npm run build                     # builds with zero errors
cd frontend && npm run dev                       # renders, console has no red

# AI
cd ai && python -m pytest tests/ -q              # or run the module directly on a sample image
```

Backend must have **zero unhandled exceptions on startup**. Frontend must have **zero console errors** on the main flows. If either fails, it is not done.

### 2.6 Health check first

At the very start of the build, create `GET /health` returning `{"status":"ok","db":"ok"}`. Use it as the smoke test after every backend change.

---

## 3. Engineering Standards

### 3.1 Code quality

- No pseudo-code. Everything you write must be executable.
- Type hints on all Python function signatures. TypeScript for all frontend code.
- Pydantic models for every request and response body — no raw dicts crossing an API boundary.
- Config in one place: `backend/app/config.py` reading from env with validation at import time.
- No file over ~300 lines. Split by responsibility.
- No duplicated logic across backend/AI — shared constants (categories, severity levels, weights) live in one module and are imported.
- Handle errors explicitly. Every endpoint returns a proper HTTP status; no 500s for expected failure paths.

### 3.2 Version discipline

- Pin dependencies at install time. `requirements.txt` with `==`, `package-lock.json` committed.
- Before using any library API you are not 100% certain about, verify against the **installed** version (`pip show`, read the package source, check the docs for that version). Library APIs change between majors — do not rely on memory.
- If a library's behavior is version-sensitive and you can't verify it, say so explicitly rather than asserting it works.

### 3.3 Environment

Target environment is **Windows 11 native** — MSYS2 UCRT64 / PowerShell / Git Bash. **No WSL, no Linux-only assumptions.**

- Use `pathlib.Path`, never hardcoded `/` path separators.
- Give PowerShell-compatible commands, and note the Git Bash variant when they differ.
- Don't assume `make`, `sh` scripts on PATH, or Unix-only tools without flagging it.
- Python venv activation: `.\.venv\Scripts\Activate.ps1` (PowerShell), `source .venv/Scripts/activate` (Git Bash).

### 3.4 Communication in responses

- Actionable output first, reasoning second.
- Structured markdown, tables for comparisons, code blocks for all code and commands.
- Distinguish clearly: verified / assumed / inferred / uncertain.
- No motivational padding, no "great question", no re-explaining what's already established.
- Flag assumptions explicitly instead of silently baking them in.

---

## 4. Scope Discipline (24-hour constraint)

**Build order is fixed. Do not jump ahead.** See `PROJECT_SPEC.md` §Milestones.

Ship the vertical slice first: `report submit → AI analyze → stored with priority → visible on dashboard`. Everything else is polish.

### Explicitly OUT of MVP scope

Do not build unless the user explicitly asks after the MVP works:

- Password reset / email verification / OAuth
- Push or email notifications
- Admin CRUD panels beyond status update
- Model training or fine-tuning (use zero-shot / pretrained only)
- Real-time websockets
- Payment, multilingual UI, mobile app, PWA offline sync
- Microservices, Kubernetes, message queues
- Test coverage targets (write tests only for the AI scoring/dedup logic)

If asked to add something out of scope, say so and ask whether to descope something else.

### Degradation rule

If an AI component fails or is slow, the app must still work. Every AI call is wrapped so a failure produces `category="unclassified", severity=3, confidence=0.0` and the report still saves. **A report submission must never fail because of the AI layer.**

---

## 5. DEVLOG.md — maintain continuously

Keep `DEVLOG.md` at the root of this `CivicLens/` folder, updated as you work. Format:

```markdown
## <timestamp> — <task>
**Done:** what shipped
**Root cause fixes:** bug → cause → fix
**Assumptions:** anything you decided without confirmation
**Known Issues:** unresolved, with impact
**Next:** immediate next step
```

This is the handoff artifact between the 4 team members. It matters more than clean commit messages.

---

## 6. Team Boundaries

Four members work in parallel. Respect file ownership to avoid merge conflicts:

| Member | Owns | Never edits |
|---|---|---|
| M1 — AI/ML | `ai/` | `frontend/`, `backend/app/routers/` |
| M2 — Backend | `backend/` | `ai/models/`, `frontend/src/` |
| M3 — Frontend | `frontend/` | `backend/`, `ai/` |
| M4 — Integration | `docker-compose.yml`, `scripts/`, `.github/`, deploy config, cross-cutting fixes | — |

Contracts (`PROJECT_SPEC.md` §API and §Schema) are **shared and frozen** once agreed. If a contract must change, update `PROJECT_SPEC.md` first, note it in `DEVLOG.md`, and flag it — never change it silently.

---

## 7. Conflict Resolution

If instructions in this file, `PROJECT_SPEC.md`, and the user's message contradict each other — **stop and ask which is authoritative**. Never silently pick one and proceed.
