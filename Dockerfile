FROM node:22-alpine AS dashboard
WORKDIR /dashboard
COPY dashboard/package.json dashboard/package-lock.json dashboard/.npmrc ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.32
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY server/ ./server/
COPY system/templates/default_brain/ ./seed_brain/
COPY scripts/container_start.py ./scripts/container_start.py
COPY --from=dashboard /dashboard/dist ./dashboard/dist/
RUN useradd --uid 10001 --create-home soloos && mkdir /data && chown soloos:soloos /data
ENV BDSG_DATA_DIR=/data PATH=/app/.venv/bin:$PATH
USER soloos
EXPOSE 8000
CMD ["python", "scripts/container_start.py"]
