# FROM python:3.11-slim

# WORKDIR /app

# # System deps needed by chromadb / sentence-transformers
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential curl \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .
# RUN mkdir -p data/chroma data/uploads data/csvs

# EXPOSE 8000

# # Default command runs the API; Render's worker service overrides this
# # with the Celery command (see render.yaml).
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/chroma data/uploads data/csvs

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000

CMD ["/start.sh"]