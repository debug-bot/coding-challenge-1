[![Tests](https://github.com/debug-bot/coding-challenge-1/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/debug-bot/coding-challenge-1/actions/workflows/tests.yml)
[![Docker](https://github.com/debug-bot/coding-challenge-1/actions/workflows/docker.yml/badge.svg?branch=main)](https://github.com/debug-bot/coding-challenge-1/actions/workflows/docker.yml)


# 🐾 Animals ETL Challenge

This repository implements a **resilient ETL client** (`loader.py`) that connects to the **provided Animals API Docker image** (`lp-programming-challenge-1:latest`) to extract, transform, and load animal data while handling real-world API instability.

The system demonstrates fault-tolerant data engineering practices, handling slow responses, transient 5xx errors, and batch processing with concurrency.

---

## 📘 Overview

### Components

| Component                | Description                                                                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`loader.py`**          | Async ETL client that connects to the provided API, fetches all animal data, applies transformations, and posts batches of ≤100 animals to `/animals/v1/home`. |
| **`docker-compose.yml`** | Runs both the provided API container and the loader in a single network. The loader waits for the API to become healthy before starting.                       |
| **`Dockerfile`**         | Builds a lightweight image for the loader (Python 3.13) containing all dependencies (httpx, pytest, pytest-asyncio).                                           |

---

## ⚙️ Features

### 🦶 Loader (`loader.py`)

* Fully **asynchronous** using `httpx` and `asyncio`.
* Automatically retries transient 500–504 errors with **exponential backoff and jitter**.
* Handles **timeouts ≥ 45s** to survive real 5–15s delays.
* Fetches all animal pages, retrieves detailed info concurrently, transforms data, and uploads in batches of ≤100.
* Configurable via CLI or environment variables.

---

## 🔄 ETL Process

| Step           | Description                                                                       |
| -------------- | --------------------------------------------------------------------------------- |
| **Extract**    | Fetch all animals from `/animals/v1/animals` (paginated).                         |
| **Transform**  | Convert:<br>• `friends` → array of strings<br>• `born_at` → ISO8601 UTC timestamp |
| **Load**       | POST animals in batches of ≤100 to `/animals/v1/home`.                            |
| **Resilience** | Retries on 500–504 and gracefully handles real API delays (5–15s).                |

---

## 🧯 Requirements

| Tool           | Version                       |
| -------------- | ----------------------------- |
| Python         | 3.11 - 3.13                   |
| Docker         | 20+                           |
| docker-compose | 1.29+                         |
| Dependencies   | httpx, pytest, pytest-asyncio |
| Formatter      | Black 24.8.0                  |
| Pre-commiiter  | 3.8.0                         |

---

## 🐳 Running with Docker (Required)

### 1️⃣ Load the provided API image

```bash
docker load -i lp-programming-challenge-1-*.tar.gz
```

### 2️⃣ Build and start the loader with the API

```bash
docker compose up --build
```

This command:

* Starts the **provided API** (`lp-programming-challenge-1:latest`) on port **3123**.
* Builds and runs the **loader** container.
* Waits until the API healthcheck (`GET /` → `Hello!`) passes before executing.

#### Expected output

```
animals_api    | Serving on http://0.0.0.0:3123
animals_loader | Fetching animals from http://api:3123/animals/v1/animals …
animals_loader | Retrying (503)… backoff 2s
animals_loader | ✅ Loaded 5520 animals successfully
```

---

## 🔍 Healthcheck

* The API is healthy when `curl http://localhost:3123/` returns `Hello!`.
* Docker Compose uses a built-in healthcheck to ensure the loader waits for the API.

---

## 🤪 Testing

Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest -v
```

The test suite covers:

* Pagination and ETL flow logic
* Retry/backoff behavior for 5xx and timeout scenarios
* Data transformation (friends → list, born_at → ISO8601 UTC)
* Batch posting correctness

---

## 🧹 Code Style (Black & Pre-commit)

To ensure consistent formatting, this project uses [Black](https://black.readthedocs.io/en/stable/) and [pre-commit](https://pre-commit.com/).

Install and run:

```bash
pip install black pre-commit
pre-commit install
black .

---
```md
## 🧩 CI/CD Pipeline

GitHub Actions runs full CI/CD for this repository:

* ✅ **Black + Pre-commit** style checks  
* ✅ **Unit tests** (pytest, pytest-asyncio) across Python 3.11–3.13  
* ✅ **Docker image build and push to GHCR**

```yaml
python-version: ["3.11", "3.12", "3.13"]
The Docker workflow builds and publishes the loader image to:
`ghcr.io/debug-bot/coding-challenge-1/animals-loader`

---

## 🗾 Configuration

| Parameter       | Description                          | Default           |
| --------------- | ------------------------------------ | ----------------- |
| `--base-url`    | Base URL of the API                  | `http://api:3123` |
| `--concurrency` | Concurrent requests for detail pages | `32`              |
| `--batch-size`  | Max POST batch size                  | `100`             |

---

## 📦 Project Structure

```
.
├── loader.py
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .github/workflows/tests.yml
├── .github/workflows/docker.yml
├── .pre-commit-config.yaml
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── wait_for_api.py
├── pyproject.toml
├── tests/
│   ├── __init__.py
│   └── test_loader.py
└── README.md
```

---

## ✅ Compliance Summary

| Requirement                                 | Status  | Notes                                           |
| ------------------------------------------- | ------  | ----------------------------------------------- |
| **Uses provided API Docker image**          | ✅      | Connects to lp-programming-challenge-1:latest   |
| **Connects to real API**                    | ✅      | Targets `lp-programming-challenge-1:latest`     |
| **Handles real chaos (5–15s delays + 5xx)** | ✅      | Backoff, retries, and long timeouts implemented |
| **Fetch all animals**                       | ✅      | Full pagination supported                       |
| **Transform fields**                        | ✅      | friends → list, born_at → ISO8601 UTC           |
| **Batch upload (≤100)**                     | ✅      | Enforced by loader                              |
| **Parallelism**                             | ✅      | Async concurrency via asyncio/httpx             |
| **Error handling & tests**                  | ✅      | Extensive pytest coverage                       |
| **CI/CD**                                   | ✅      | GitHub Actions pipeline                         |

---

## 🧠 Notes

* The solution uses the official Animals API Docker image provided in the challenge.
* All data retrieval and transformations occur against the **real API**.
* The loader is fully resilient to API delays and HTTP 5xx responses.

---

## 🗾 License

MIT License © 2025

---

### ✨ Example End-to-End Command

```bash
docker load -i lp-programming-challenge-1-*.tar.gz && docker compose up --build
```

→ Brings up the provided API and runs the loader automatically after healthcheck passes.
