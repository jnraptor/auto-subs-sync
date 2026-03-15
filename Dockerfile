# Stage 1: Build alass from source
FROM rust:slim AS alass-builder
RUN apt-get update && apt-get install -y git
RUN cargo install alass-cli

# Stage 2: Python builder
FROM python:slim AS python-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Runtime
FROM python:slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=alass-builder /usr/local/cargo/bin/alass-cli /usr/local/bin/alass
COPY --from=python-builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

EXPOSE 8080

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
