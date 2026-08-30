FROM thehale/python-poetry:2.4.1-py3.14-slim AS requirements
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install

FROM python:3.14-slim AS main
COPY --from=requirements /app/.venv /app/.venv
COPY . /app/
RUN groupadd --gid 1000 nonroot && useradd --uid 1000 --gid 1000 --no-create-home --shell /bin/bash nonroot
WORKDIR /app
USER nonroot
CMD ["/app/.venv/bin/python3", "/app/main.py"]