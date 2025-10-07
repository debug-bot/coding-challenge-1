# 🐾 Animals ETL Challenge

This repository implements a **FastAPI-based mock server** (`animal_api.py`) and a **resilient ETL client** (`loader.py`) that interact through HTTP.
The project simulates real-world conditions with random latency and transient 5xx errors, testing your ability to build fault-tolerant, maintainable data pipelines.

---

## 📘 Overview

### Components

| Component                | Description                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **`animal_api.py`**      | FastAPI mock API serving animal data with randomized chaos (delays + 5xx errors).                              |
| **`loader.py`**          | Async ETL client that fetches all animal data, transforms it, and posts batches of ≤100 to `/animals/v1/home`. |
| **`docker-compose.yml`** | Spins up both API and loader containers; the loader waits for the API to be healthy before starting.           |
| **`Dockerfile`**         | Builds a single image capable of running both API and loader.                                                  |

---

## ⚙️ Features

### 🐍 FastAPI Server (`animal_api.py`)

* **Endpoints**

  * `GET /animals/v1/animals?page=<n>&per_page=<m>` — paginated listing
  * `GET /animals/v1/animals/{id}` — detailed animal info
  * `POST /animals/v1/home` — receive batches of animals (max 100)
  * `GET /` — healthcheck (`"Hello!"`)

* **Chaos Middleware**

  * Randomly sleeps 5–15 seconds.
  * Occasionally returns random 500/502/503/504 errors.
  * Simulates unreliable API conditions.

---

### 🦶 Loader (`loader.py`)

* Fully **asynchronous** using `httpx` and `asyncio`.
* Automatically retries transient errors with **exponential backoff** and jitter.
* Handles **timeouts ≥ 45s** to survive the API’s chaos delays.
* Fetches all animal pages, retrieves detailed info concurrently, transforms the data, and uploads in batches of ≤100.
* Configurable via CLI or environment variables.

---

## 🔄 ETL Process

| Step           | Description                                                                              |
| -------------- | ---------------------------------------------------------------------------------------- |
| **Extract**    | Fetch all animals from `/animals/v1/animals` (paginated).                                |
| **Transform**  | Convert: <br>• `friends` → array (split by comma)<br>• `born_at` → ISO8601 UTC timestamp |
| **Load**       | POST animals in batches of ≤100 to `/animals/v1/home`.                                   |
| **Resilience** | Retries 500–504 errors and handles 5–15s delays gracefully.                              |

---

## 🧯 Requirements

| Tool           | Version                                                   |
| -------------- | --------------------------------------------------------- |
| Python         | 3.10+                                                     |
| Docker         | 20+                                                       |
| docker-compose | 1.29+                                                     |
| Dependencies   | fastapi, uvicorn, httpx, pydantic, pytest, pytest-asyncio |

---

## 🚀 Running Locally

### 1️⃣ Install dependencies

```bash
pip install fastapi uvicorn httpx
```

### 2️⃣ Start the API

```bash
uvicorn animal_api:app --host 0.0.0.0 --port 3123 --reload
```

Visit [http://localhost:3123](http://localhost:3123) or [http://localhost:3123/docs](http://localhost:3123/docs).

### 3️⃣ Run the loader

```bash
python loader.py --base-url http://localhost:3123 --concurrency 32 --batch-size 100
```

Optional:

```bash
export ANIMALS_BASE_URL=http://localhost:3123
python loader.py
```

---

## 🐳 Running with Docker

### Build and run API only

```bash
docker compose up --build api
```

### Run API + Loader end-to-end

```bash
docker compose up --build
```

#### Expected output

```
animals_api    | INFO: Uvicorn running on http://0.0.0.0:3123
animals_loader | Listing animals from http://api:3123/animals/v1/animals …
animals_loader | Fetched 5000/5520 details
animals_loader | ✅ ETL complete
```

---

## 🔍 API Healthcheck

* `GET /` → `"Hello!"`
* API is healthy when `curl http://localhost:3123/` returns HTTP 200.

In Docker Compose, the loader waits until this healthcheck passes.

---

## 🤪 Testing

Install dev dependencies:

```bash
pip install pytest pytest-asyncio httpx
```

Run tests:

```bash
pytest -v
```

The test suite covers:

* Helper functions (`chunks`, `transform`, `to_iso8601_utc`)
* Retry logic for transient failures
* Mocked pagination and full ETL workflow via `httpx.MockTransport`

---

## 🗾 Configuration

| Parameter       | Description                                | Default                 |
| --------------- | ------------------------------------------ | ----------------------- |
| `--base-url`    | Base URL of the API                        | `http://localhost:3123` |
| `--concurrency` | Concurrent detail requests                 | `32`                    |
| `--batch-size`  | Max POST batch size                        | `100`                   |
| `VERIFY`        | Env var to enable verification mode in API | `0`                     |

---

## 📦 Project Structure

```
.
├── animal_api.py
├── animals.json
├── loader.py
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── .gitignore
├── pytest.ini
├── requirements.txt
├── tests/
│   ├── __init__.py
│   └── test_loader.py
└── README.md
```

---

## 🧠 Notes

* The **chaos middleware** intentionally causes random 5xx errors and delays to test fault tolerance.
* The **loader** is expected to recover automatically from these issues.
* Use `VERIFY=1` to track progress as the loader posts batches (prints remaining IDs).

---

## 🗾 License

MIT License © 2025

---

### ✨ Example End-to-End Command

```bash
docker compose up --build
```

→ Brings up the FastAPI API and runs the loader once the API is healthy.
