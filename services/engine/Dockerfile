# Build from the REPO ROOT:
#   docker build -f services/engine/Dockerfile -t protocol-engine .
#   docker run -p 8000:8000 -e GEMINI_API_KEY=... protocol-engine
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/models \
    PROTOCOL_DATA_DIR=/app/packages/data/processed

WORKDIR /app

COPY services/engine/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image so the first request doesn't download it.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY services/engine /app/services/engine
COPY packages/data /app/packages/data
COPY exercises-dataset /app/exercises-dataset

WORKDIR /app/services/engine
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
