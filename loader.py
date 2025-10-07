#!/usr/bin/env python3
"""
loader.py — Resilient ETL client for the Animals API.

Requirements satisfied:
- Retries on 500/502/503/504 with exponential backoff + jitter
- Generous timeouts (>= 30s) so slow requests don't crash
- Consistent flow: fetch all -> transform -> post in batches (<=100)
- Bounded concurrency for detail fetches
"""
import asyncio
import argparse
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import httpx


RETRY_STATUS = {500, 502, 503, 504}


def chunks(seq: List[Any], size: int) -> Iterable[List[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def to_iso8601_utc(ms: Optional[Any]) -> Optional[str]:
    if ms in (None, "", 0):
        return None
    try:
        # Convert string to int if necessary
        if isinstance(ms, str):
            if not ms.strip().isdigit():
                return None
            ms = int(ms)
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception:
        return None


def transform(detail: Dict[str, Any]) -> Dict[str, Any]:
    friends_value = detail.get("friends", [])
    if isinstance(friends_value, str):
        friends = [f for f in friends_value.split(",") if f]
    elif isinstance(friends_value, list):
        friends = friends_value
    else:
        friends = []

    return {
        "id": detail["id"],
        "name": detail["name"],
        "friends": friends,
        "born_at": to_iso8601_utc(detail.get("born_at")),
    }


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Dict[str, Any] | None = None,
    max_retries: int = 6,
    connect_timeout: float = 5.0,
    read_timeout: float = 45.0,  # >= 30s to tolerate 5–15s chaos delays
) -> Dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        try:
            r = await client.get(url, params=params, timeout=httpx.Timeout(read_timeout, connect=connect_timeout))
            if r.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            if attempt >= max_retries:
                raise
            # Exponential backoff with a little deterministic jitter
            backoff = min(30, (2 ** attempt)) + (attempt * 0.137)
            await asyncio.sleep(backoff)


async def post_json(
    client: httpx.AsyncClient,
    url: str,
    payload: Any,
    *,
    max_retries: int = 6,
    connect_timeout: float = 5.0,
    read_timeout: float = 45.0,
) -> Dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        try:
            r = await client.post(url, json=payload, timeout=httpx.Timeout(read_timeout, connect=connect_timeout))
            if r.status_code in RETRY_STATUS:
                raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError):
            if attempt >= max_retries:
                raise
            backoff = min(30, (2 ** attempt)) + (attempt * 0.137)
            await asyncio.sleep(backoff)


async def fetch_all_ids(client: httpx.AsyncClient, list_url: str) -> List[int]:
    # Fetch first page to get total_pages
    first = await get_json(client, list_url, params={"page": 1})
    total_pages = int(first["total_pages"])
    ids = [item["id"] for item in first["items"]]

    # Remaining pages
    for page in range(2, total_pages + 1):
        data = await get_json(client, list_url, params={"page": page})
        ids.extend(item["id"] for item in data["items"])
    return ids


async def fetch_detail(
    client: httpx.AsyncClient,
    detail_url_tmpl: str,
    animal_id: int,
    sem: asyncio.Semaphore,
) -> Dict[str, Any]:
    async with sem:
        detail = await get_json(client, detail_url_tmpl.format(id=animal_id))
        return transform(detail)


async def run(base_url: str, concurrency: int = 32, batch_size: int = 100):
    list_url = f"{base_url}/animals/v1/animals"
    detail_url = f"{base_url}/animals/v1/animals/{{id}}"
    home_url = f"{base_url}/animals/v1/home"

    sem = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient() as client:
        print(f"Listing animals from {list_url} …")
        ids = await fetch_all_ids(client, list_url)
        total = len(ids)
        print(f"Total animals detected: {total}")

        print(f"Fetching details concurrently (concurrency={concurrency}) …")
        details: List[Dict[str, Any]] = []
        # Process in manageable groups to avoid gigantic gather lists
        group_size = 5000
        for i in range(0, total, group_size):
            group = ids[i:i + group_size]
            details.extend(await asyncio.gather(*(fetch_detail(client, detail_url, _id, sem) for _id in group)))
            print(f"Fetched {len(details)}/{total} details")

        print(f"Posting to {home_url} in batches of {batch_size} …")
        sent = 0
        for batch in chunks(details, batch_size):
            resp = await post_json(client, home_url, batch)
            sent += len(batch)
            print(f"{sent}/{total} → {resp.get('message')}")

    print("✅ ETL complete")


def parse_args():
    p = argparse.ArgumentParser(description="Resilient Animals API ETL loader")
    p.add_argument("--base-url", default=os.environ.get("ANIMALS_BASE_URL", "http://localhost:3123").rstrip("/"),
                   help="Base URL of the Animals API (default: http://localhost:3123 or $ANIMALS_BASE_URL)")
    p.add_argument("--concurrency", type=int, default=32, help="Concurrent detail requests (default: 32)")
    p.add_argument("--batch-size", type=int, default=100, help="POST batch size, max 100 (default: 100)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.base_url, args.concurrency, args.batch_size))
