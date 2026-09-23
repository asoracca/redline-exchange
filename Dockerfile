FROM node:22-bookworm-slim AS frontend
WORKDIR /build/web
RUN npm install --global pnpm@11.19.0
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/src
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY cpp/ ./cpp/
COPY scripts/build_native.py ./scripts/build_native.py
RUN pip install --no-cache-dir '.[demo,native]' && python scripts/build_native.py
COPY --from=frontend /build/web/dist ./web/dist
COPY deploy.py ./deploy.py
RUN useradd --create-home --uid 10001 redline
USER redline
EXPOSE 10000
CMD ["python", "deploy.py"]
