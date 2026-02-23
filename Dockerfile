FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libcairo2 \
        libffi-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpq-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ${APP_HOME}/requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r ${APP_HOME}/requirements.txt

COPY . ${APP_HOME}

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p ${APP_HOME}/logs ${APP_HOME}/media ${APP_HOME}/staticfiles \
    && chmod +x ${APP_HOME}/deploy/entrypoint.sh ${APP_HOME}/deploy/worker.sh \
    && chown -R appuser:appuser ${APP_HOME}

USER appuser

EXPOSE 8000

CMD ["/app/deploy/entrypoint.sh"]
