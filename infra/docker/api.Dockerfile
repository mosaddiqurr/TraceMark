FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system tracemark && useradd --system --gid tracemark --create-home tracemark
WORKDIR /app

COPY packages/watermark_engine ./packages/watermark_engine
COPY apps/api ./apps/api
RUN python -m pip install --upgrade pip && \
    python -m pip install ./packages/watermark_engine ./apps/api

USER tracemark
EXPOSE 8000
CMD ["sh", "-c", "cd /app/apps/api && alembic upgrade head && exec uvicorn tracemark_api.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
