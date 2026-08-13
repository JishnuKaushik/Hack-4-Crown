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
