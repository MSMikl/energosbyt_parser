# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm as builder
WORKDIR /install
RUN apt-get update && apt-get install -y build-essential
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --wheel-dir /wheels -r requirements.txt

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt
COPY . .

ENV PYTHONPATH=/app:$PYTHONPATHWORKDIR
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
