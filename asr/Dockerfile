FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ffmpeg : requis par yt-dlp (extraction audio) et WhisperX (decodage audio).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Dependances Python (couche mise en cache tant que requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8100

# start-period long : le premier appel telecharge les modeles Whisper/pyannote.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
