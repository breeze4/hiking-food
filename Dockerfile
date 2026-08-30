FROM node:22.14.0-bookworm-slim@sha256:745403dc46b5ab4c998502b07a12cbf020cf2c30645427a68ec0718f02d647de AS frontend

WORKDIR /build/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && corepack prepare pnpm@11.5.1 --activate && pnpm install --frozen-lockfile
COPY frontend ./
RUN pnpm build

FROM python:3.12.13-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

ARG VCS_REF
LABEL org.opencontainers.image.source="https://github.com/breeze4/hiking-food"
LABEL org.opencontainers.image.revision="${VCS_REF}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    HIKING_FOOD_DATABASE_URL=sqlite:////data/hiking_food.db \
    HIKING_FOOD_AUTH_DB_PATH=/data/hiking_food_auth.db \
    HIKING_FOOD_BACKUP_DIR=/data/backups

RUN groupadd --gid 1000 hikingfood \
  && useradd --uid 1000 --gid hikingfood --create-home hikingfood

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY backend ./backend
COPY --from=frontend /build/frontend/dist ./frontend/dist
RUN chown -R 1000:1000 /app

USER 1000:1000
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/hiking-food/api/health', timeout=2).read()"
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "/app/backend"]
