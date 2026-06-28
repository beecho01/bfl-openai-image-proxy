# Chainguard hardened Python image: minimal, non-root by default, fast CVE patching.
# Pin by digest in production for reproducibility.
FROM chainguard/python:3.12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps as root (builder), then drop back to the built-in nonroot user.
USER root
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Create the generated-image dir and hand it to the nonroot user (UID 65532).
RUN mkdir -p /tmp/bfl-openai-image-proxy/generated \
    && chown -R nonroot:nonroot /tmp/bfl-openai-image-proxy /app

USER nonroot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5); sys.exit(0)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]