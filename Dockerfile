# Python 3.12 slim base. Runs as a non-root user with a minimal footprint.
# To use the Chainguard hardened image instead, use `FROM chainguard/python:latest`
# (ships Python 3.14) and drop the useradd block — but verify dependency compat first.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /tmp/bfl-openai-image-proxy/generated \
    && chown -R appuser:appuser /tmp/bfl-openai-image-proxy /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5); sys.exit(0)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]