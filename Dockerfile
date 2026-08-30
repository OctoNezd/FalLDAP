FROM thehale/python-poetry:2.4.1-py3.14-slim AS requirements
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install

FROM python:3.14-slim AS main
RUN pip install supervisor
WORKDIR /app
COPY --from=requirements /app/.venv /app/.venv
RUN groupadd --gid 1000 nonroot && useradd --uid 1000 --gid 1000 --no-create-home --shell /bin/bash nonroot
COPY ./static /app/static/
COPY ./templates /app/templates/
COPY *.py /app/
COPY ./blueprints /app/blueprints
COPY supervisord.conf /app/
USER nonroot
ENV HTTP_PORT=8080
ENV LDAP_PORT=8389
ENV HTTP_HOST=0.0.0.0
ENV LDAP_HOST=0.0.0.0
ENV TRUST_PROXY=127.0.0.0/8
ENV HOME=/tmp
EXPOSE 8080 8389
CMD ["supervisord"]
LABEL org.opencontainers.image.source=https://github.com/octonezd/falldap