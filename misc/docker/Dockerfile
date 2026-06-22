#################
# Base Image
#################
FROM python:3.11-slim as base

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

#################
# Builder Image
#################
FROM base as builder

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

#################
# Final Image
#################
FROM base

ENV PYTHONUNBUFFERED=1

COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000
