import time
import requests


def hf_post(url: str, payload: dict, token: str, retries: int = 3, backoff_base: float = 2.0) -> list | dict:
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(retries):
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json()
        if attempt < retries - 1:
            time.sleep(backoff_base ** attempt)
    raise RuntimeError(f"HF API failed after {retries} attempts: {resp.status_code} {resp.text[:200]}")
