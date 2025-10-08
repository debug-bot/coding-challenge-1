# wait_for_api.py
import os
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

URL = os.environ.get("WAIT_URL", "http://api:3123/")
TIMEOUT_SECONDS = int(os.environ.get("WAIT_TIMEOUT", "180"))  # default 3 min

print(f"Waiting for API at {URL} (timeout {TIMEOUT_SECONDS}s)...", flush=True)
deadline = time.time() + TIMEOUT_SECONDS

attempt = 0
while time.time() < deadline:
    attempt += 1
    try:
        with urlopen(URL, timeout=3) as r:
            code = getattr(r, "status", 200)  # py311 returns .status
            if 200 <= code < 400:
                print(f"API is up! HTTP {code}", flush=True)
                sys.exit(0)
    except (URLError, HTTPError) as e:
        # e.code for HTTPError, e.reason for URLError
        pass
    time.sleep(1)

print("API not ready in time.", flush=True)
sys.exit(1)
