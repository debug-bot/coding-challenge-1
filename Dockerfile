# Dockerfile for Animals API + loader (Python 3.13)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# (Optional but handy) curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Option A: install minimal runtime deps directly ---
# If you don't maintain a requirements.txt, this is fine:
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic

# --- Option B: use requirements file instead (recommended) ---
# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt

# Add app code
COPY . /app

EXPOSE 3123

# Default: run the API
CMD ["uvicorn", "animal_api:app", "--host", "0.0.0.0", "--port", "3123"]
