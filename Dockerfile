# Dockerfile (loader-only)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies for runtime client
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only what the loader needs
COPY loader.py wait_for_api.py ./

# Default to running the loader; can be overridden by docker-compose
CMD ["python", "loader.py"]
