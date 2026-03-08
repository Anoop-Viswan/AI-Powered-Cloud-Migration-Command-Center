# Multi-stage: build frontend, then run backend + serve static
# Use for Hugging Face Spaces (Docker Space) or any container cloud (AWS ECS, GCP Cloud Run, etc.)

# ---- Frontend ----
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev
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

# App code
COPY backend/ ./backend/
COPY semantic_search.py document_extractors.py usage_tracker.py ./
COPY manifest.json.example ./

# Built frontend → static (so FastAPI can serve it)
COPY --from=frontend /app/frontend/dist ./static

# Default project dir for docs (override with env; mount a volume over /data to provide documents)
RUN mkdir -p /data
ENV PINECONE_PROJECT_DIR=/data
EXPOSE 7860

# Hugging Face Spaces expect server on 7860; use 0.0.0.0 so it’s reachable
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
