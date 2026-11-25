FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=backend.settings_production

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 libmagic1 poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system xggaffer \
    && useradd --system --gid xggaffer --create-home xggaffer

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=xggaffer:xggaffer . /app

RUN mkdir -p /app/staticfiles /app/media /app/data \
    && chown -R xggaffer:xggaffer /app/staticfiles /app/media /app/data

USER xggaffer

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "backend.wsgi:application"]
