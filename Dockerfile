FROM python:3.10

RUN /usr/local/bin/python -m pip install --upgrade pip
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$PYTHONPATH:/app" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get upgrade -y \
    && apt-get install --no-install-recommends -y \
    gcc \
    curl \
    && curl -sSL 'https://install.python-poetry.org' | python \
    && poetry --version \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi

# Создаем README.md чтобы избежать ошибки Poetry
RUN touch /app/README.md

# Копируем оба сервиса
COPY provider/ ./provider/
COPY aggregator/ ./aggregator/