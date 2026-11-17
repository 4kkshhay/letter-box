# syntax=docker/dockerfile:1@sha256:4edf897a3ffa55b89f906fc8cc78afdb3f1834cc9c7083565e611a8a7d5fe99e

# Build the pages to static files. Node is not part of the runtime image.
FROM node:24-slim@sha256:dc26ae92c9fb15cf6b1d63e20f0944b2efe0f115b20e00be48fb23fceb061c54 AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# Frontend tests: docker build --target frontend-test
FROM frontend AS frontend-test
RUN npm test

# Python app plus the built pages.
FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY --from=frontend /build/dist ./static

# Backend tests: docker build --target test
FROM base AS test
COPY backend/requirements-dev.txt backend/pyproject.toml ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements-dev.txt
COPY backend/tests ./tests
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

# Runtime image (default target).
FROM base AS app
EXPOSE 8000 8001
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --start-interval=1s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2)"]
CMD ["python", "-m", "app.serve"]
