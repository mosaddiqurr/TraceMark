FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system tracemark && useradd --system --gid tracemark --create-home tracemark
WORKDIR /app

COPY packages/watermark_engine ./packages/watermark_engine
COPY apps/api ./apps/api
COPY workers ./workers
RUN python -m pip install --upgrade pip && \
    python -m pip install ./packages/watermark_engine ./apps/api && \
    python -m pip install "dramatiq[redis]"

ENV PYTHONPATH=/app/workers
USER tracemark
CMD ["dramatiq", "tracemark_worker.tasks", "--processes", "1", "--threads", "2"]
