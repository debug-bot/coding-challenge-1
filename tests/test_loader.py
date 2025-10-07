"""
Unit tests for loader.py

Covers:
- pure helpers (chunks, to_iso8601_utc, transform)
- retry logic for GET/POST with httpx.MockTransport
- end-to-end happy path using a mocked API (pagination -> details -> post)
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
import pytest

# Import targets from loader.py
from loader import chunks, to_iso8601_utc, transform, get_json, post_json, fetch_all_ids


# ---------------------------
# Pure helper tests
# ---------------------------

def test_chunks_basic():
    # chunks should split a list into fixed-size pieces
    data = list(range(7))
    out = list(chunks(data, 3))
    assert out == [[0, 1, 2], [3, 4, 5], [6]]


def test_to_iso8601_utc_numeric():
    # 1609459200000 = 2021-01-01T00:00:00Z
    iso = to_iso8601_utc(1609459200000)
    assert iso.startswith("2021-01-01T00:00:00")
    assert iso.endswith("Z")


def test_to_iso8601_utc_string_and_invalid():
    # string numeric is okay
    iso = to_iso8601_utc("1609459200000")
    assert iso.startswith("2021-01-01T00:00:00")
    # non-numeric returns None
    assert to_iso8601_utc("abc") is None
    # empty / None return None
    assert to_iso8601_utc("") is None
    assert to_iso8601_utc(None) is None


def test_transform_friends_and_born_at():
    # friends as comma string
    d1 = {"id": 1, "name": "Cat", "friends": "Dog,Elephant", "born_at": 1609459200000}
    t1 = transform(d1)
    assert t1["friends"] == ["Dog", "Elephant"]
    assert t1["born_at"].startswith("2021-01-01T00:00:00")

    # friends already as list
    d2 = {"id": 2, "name": "Dog", "friends": ["Cat", "Elephant"], "born_at": None}
    t2 = transform(d2)
    assert t2["friends"] == ["Cat", "Elephant"]
    assert t2["born_at"] is None

    # friends missing -> []
    d3 = {"id": 3, "name": "Elephant"}
    assert transform(d3)["friends"] == []


# ---------------------------
# Retry logic tests (GET/POST)
# ---------------------------

@pytest.mark.asyncio
async def test_get_json_retries_then_succeeds():
    """
    Simulate two transient 500s then a 200.
    Ensure get_json retries and finally returns JSON.
    """
    attempts = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 3:
            return httpx.Response(500, text="flaky")
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        data = await get_json(client, "http://test")
        assert data == {"ok": True}
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_post_json_retries_then_succeeds():
    """
    Simulate a transient 503 then 200 on POST.
    Ensure post_json retries and returns body.
    """
    attempts = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(503, text="busy")
        # Echo the JSON payload back to us on success
        body = json.loads((await request.aread()).decode() or "null")
        return httpx.Response(200, json={"received": body})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        payload = [{"id": 1}]
        resp = await post_json(client, "http://test", payload)
        assert resp["received"] == payload
    assert attempts["n"] == 2


# ---------------------------
# End-to-end (mocked) flow tests
# ---------------------------

@pytest.mark.asyncio
async def test_fetch_all_ids_pagination():
    """
    Mock pagination: total_pages=3 with 2 items per page.
    Verify fetch_all_ids aggregates all IDs.
    """
    pages = {
        "1": {"items": [{"id": 0}, {"id": 1}], "page": 1, "total_pages": 3},
        "2": {"items": [{"id": 2}, {"id": 3}], "page": 2, "total_pages": 3},
        "3": {"items": [{"id": 4}, {"id": 5}], "page": 3, "total_pages": 3},
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        # Parse query param page
        q = httpx.QueryParams(request.url.query)
        page = q.get("page", "1")
        return httpx.Response(200, json=pages[page])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        ids = await fetch_all_ids(client, "http://test/animals/v1/animals")
        assert ids == [0, 1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_full_flow_mocked_details_and_post():
    """
    End-to-end happy path with mock endpoints:
      - GET /animals/v1/animals?page=... returns IDs
      - GET /animals/v1/animals/{id} returns detail with friends as str
      - POST /animals/v1/home accepts batches and responds
    Ensures transform + batching works as expected.
    """
    # Prepare fake pages: 1 page, 3 animals
    list_payload = {"items": [{"id": 10}, {"id": 11}, {"id": 12}], "page": 1, "total_pages": 1}

    # Fake details: friends comma string, born_at epoch ms
    details: Dict[int, Dict[str, Any]] = {
        10: {"id": 10, "name": "Cat", "friends": "Dog,Elephant", "born_at": 1609459200000},
        11: {"id": 11, "name": "Dog", "friends": "", "born_at": None},
        12: {"id": 12, "name": "Elephant", "friends": "Cat", "born_at": "1609459200000"},
    }

    posted_batches: List[List[Dict[str, Any]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/animals/v1/animals" in url and request.method == "GET":
            # Listing vs details?
            if request.url.path.endswith("/animals"):
                return httpx.Response(200, json=list_payload)
            else:
                # Detail route: extract id from path
                animal_id = int(request.url.path.split("/")[-1])
                return httpx.Response(200, json=details[animal_id])

        if request.method == "POST" and request.url.path.endswith("/animals/v1/home"):
            body = json.loads((await request.aread()).decode() or "[]")
            posted_batches.append(body)
            return httpx.Response(200, json={"message": f"Helped {len(body)} find home"})


        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        # Reuse fetch_all_ids + get_json for details + emulate transform+post
        ids = await fetch_all_ids(client, "http://x/animals/v1/animals")

        # Transform each detail and batch post
        transformed = []
        for _id in ids:
            r = await httpx.AsyncClient(transport=transport).__aenter__()  # create ephemeral client for detail
            try:
                detail = (await r.get(f"http://x/animals/v1/animals/{_id}")).json()
            finally:
                await r.aclose()

            t = transform(detail)
            transformed.append(t)

        # Post them in batches of 2
        for i in range(0, len(transformed), 2):
            batch = transformed[i: i + 2]
            # Use post_json to exercise retry wrapper as well (here 200 immediate)
            resp = await post_json(httpx.AsyncClient(transport=transport), "http://x/animals/v1/home", batch)
            assert "Helped" in resp["message"]

    # Validate the batches we "posted" were transformed correctly
    assert len(posted_batches) == 2  # 3 items with batch size 2 → 2 POSTs
    # First batch (ids 10, 11)
    b0 = posted_batches[0]
    assert b0[0]["friends"] == ["Dog", "Elephant"]
    assert b0[0]["born_at"].startswith("2021-01-01T00:00:00")
    assert b0[1]["friends"] == []
    assert b0[1]["born_at"] is None
    # Second batch (id 12)
    b1 = posted_batches[1]
    assert b1[0]["friends"] == ["Cat"]
    assert b1[0]["born_at"].startswith("2021-01-01T00:00:00")
