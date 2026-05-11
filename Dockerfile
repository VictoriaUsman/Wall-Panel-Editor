# Stage 1 — build the React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2 — Python backend
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy built frontend so FastAPI can serve it
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "python seed.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
