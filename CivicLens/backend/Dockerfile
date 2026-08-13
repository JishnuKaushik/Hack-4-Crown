# UNVERIFIED: not build-tested (no Docker available in the dev environment
# this was written in). Review/test before relying on it for a real deploy.
#
# Build context must be the REPO ROOT, not backend/, since this needs both
# backend/ and ai/ (siblings — see backend/app/__init__.py's sys.path
# bootstrap, which assumes that layout):
#   docker build -f backend/Dockerfile -t civiclens-backend .
FROM python:3.12-slim

WORKDIR /app

# Copy just the requirements files first so dependency installs are cached
# across rebuilds that only change application code.
COPY backend/requirements.txt backend/requirements.txt
COPY ai/requirements.txt ai/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY ai/ ai/

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
