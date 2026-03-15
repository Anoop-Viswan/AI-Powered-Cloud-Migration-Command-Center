# Multi-stage: build frontend, then run backend + serve static
# Use for Hugging Face Spaces (Docker Space) or any container cloud (AWS ECS, GCP Cloud Run, etc.)

# ---- Frontend ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Backend + static ----
FROM python:3.11-slim
WORKDIR /app

# System deps if needed (e.g. for PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code (semantic_search, document_extractors, usage_tracker live under backend/)
COPY backend/ ./backend/
COPY manifest.json.example ./

# Built frontend → static (so FastAPI can serve it)
COPY --from=frontend /app/frontend/dist ./static

# Default project dir for docs (override with env; mount a volume over /data to provide documents)
RUN mkdir -p /data
ENV PINECONE_PROJECT_DIR=/data
EXPOSE 7860

# Hugging Face Spaces expect server on 7860; use 0.0.0.0 so it’s reachable
# Use PORT env if set (e.g. Render sets PORT=10000); default 7860 for Hugging Face / local
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
