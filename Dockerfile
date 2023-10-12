# syntax=docker/dockerfile:1
FROM python:3.11.6-alpine3.18
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
