# syntax=docker/dockerfile:1

FROM node:22-alpine AS tailwind
WORKDIR /build
COPY package.json tailwind.config.js ./
COPY app/static/css/input.css ./app/static/css/input.css
COPY app/templates ./app/templates
RUN npm install && npm run build:css

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini seed.py ./
COPY --from=tailwind /build/app/static/css/output.css ./app/static/css/output.css
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
