# syntax=docker/dockerfile:1.7
# Multi-stage build: a fat builder, a trim runtime. The runtime stage
# never sees gcc, never runs as root, and never sees the .env file.

FROM python:3.12-slim AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
# uid 10001 keeps us safely above any real-user range; chown'ing the
# app dir means we don't need to be root at runtime.
RUN groupadd -r app -g 10001 && useradd -r -g app -u 10001 -d /app -s /usr/sbin/nologin app
COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=app:app . /app
USER app
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status==200 else 1)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
