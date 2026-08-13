# SETUP.md — How to use these files

## 1. File placement

```
civiclens/
├── CLAUDE.md              ← agent rules (auto-read by Claude Code every session)
├── PROJECT_SPEC.md        ← architecture + contracts
├── SETUP.md               ← this file (optional to keep)
├── DEVLOG.md              ← create empty, agent maintains it
├── .gitignore
├── .env.example
└── scripts/
    └── check-secrets.sh   ← rename from check-secrets.sh, put it here
```

```powershell
mkdir civiclens; cd civiclens
git init
mkdir scripts
# copy CLAUDE.md, PROJECT_SPEC.md, .gitignore, .env.example → repo root
# copy check-secrets.sh → scripts/
New-Item DEVLOG.md -ItemType File
```

Install the hook (Git Bash / MSYS2):
```bash
cp scripts/check-secrets.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
bash scripts/check-secrets.sh    # verify it runs
```

> On Windows, `.git/hooks/pre-commit` runs via Git for Windows' bundled bash — no extra setup needed. Verify with a throwaway commit before you trust it.

---

## 2. Before the first prompt — answer these

`PROJECT_SPEC.md` §11 lists 4 open decisions. Answer them in your first message or the agent will assume the defaults (FastAPI + React + Leaflet + SQLite + full JWT + heuristic severity) and log the assumption.

---

## 3. Kickoff prompts — feed in order, one per phase

Do **not** paste all of these at once. Each phase must run before the next starts.

### P0 — Skeleton (target: 2h)
```
Read CLAUDE.md and PROJECT_SPEC.md fully before doing anything.

Build Phase P0 only:
- Repo scaffold per PROJECT_SPEC §3
- backend/app/{main,config,database,models,schemas}.py — tables created on startup
- GET /health returning {"status":"ok","db":"ok"}
- Vite + React + TS + Tailwind frontend that renders a placeholder page
- requirements.txt and package.json with pinned versions

Gate before you stop:
1. uvicorn boots with zero exceptions
2. curl http://localhost:8000/health returns 200
3. npm run build completes with zero errors
4. bash scripts/check-secrets.sh exits clean

Run all four yourself and paste the actual output. Do not start P1.
```

### P1 — Vertical slice
```
Phase P1 per PROJECT_SPEC §9. AI is STUBBED — analyze_image() returns
category="pothole", confidence=0.5, severity=3, zeros embedding.

Build: POST /reports (multipart, validated upload, UUID filename),
GET /reports with filters, priority score from scoring.py, citizen
submit form wired to the real endpoint.

Gate: submit a real photo from the UI, show me the DB row and the
GET /reports response. Then commit.
```

### P2 — AI online
```
Phase P2. Implement ai/ per PROJECT_SPEC §7 and wire it into POST /reports.

Verify the installed open_clip/transformers version before using its API —
do not write from memory.

Model loads ONCE at startup. analyze_image() must never raise.
Gate: kill the model load deliberately and confirm submissions still
succeed with the fallback. Then run 3 real photos and show me the
categories and priority scores.
```

### P3 — Dedup + dashboard
```
Phase P3. Duplicate detection (3 gates, geo+time filter BEFORE similarity),
merge logic, authority dashboard with sort/filter, PATCH status + history.

Gate: two similar photos 50m apart → one canonical entry with
report_count=2. Show me the actual API responses proving it.
```

### P4 — Map + tracking
```
Phase P4. Leaflet map with priority-colored markers, citizen /track view,
JWT auth enforced, authority endpoints role-gated.

Gate: all 4 demo success criteria in PROJECT_SPEC §1 pass. Walk through
each one and show evidence.
```

### P5 — Harden
```
Phase P5. Error/loading states everywhere, input validation, seed script
for 15-20 Gurugram reports across all statuses, README.

Gate: set AI_ENABLED=false → submissions still work end to end.
```

### P6 — Deploy
```
Phase P6. Deploy config + README deploy steps.

Before you touch anything: run bash scripts/check-secrets.sh and
git log -p --all | grep -iE "secret_key|api_key|password" | head -20
Report findings first. Env vars go in the platform UI, never in a commit.
```

---

## 4. Recovery prompts

**When it drifts into batch-writing without testing:**
```
Stop. CLAUDE.md §2.1 — run what you just wrote before writing anything else.
Paste the actual output.
```

**When it claims something is fixed:**
```
Show me the command you ran and its real output. CLAUDE.md §2.3.
```

**When it goes off-scope:**
```
That's in CLAUDE.md §4 OUT of scope. Get back to phase P<n>.
```

**Before every push:**
```
Run bash scripts/check-secrets.sh, then git diff --cached and read it.
Report what's staged before you commit.
```

---

## 5. What this setup does NOT do

- The secret scanner is regex-based — it catches common patterns, not everything. **It is a safety net, not a guarantee.** Read your diffs.
- `--no-verify` bypasses the hook. Don't teach your team that flag.
- If a key is ever pushed, rotating the credential is the only real fix. History rewriting doesn't un-leak it.
