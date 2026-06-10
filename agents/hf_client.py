import time
import requests

# HuggingFace Inference API — try new router URL first, fall back to legacy
HF_ROUTER_URL = "https://router.huggingface.co/hf-inference/models"
HF_LEGACY_URL = "https://api-inference.huggingface.co/models"


def hf_post(url: str, payload: dict, token: str, retries: int = 3, backoff_base: float = 2.0) -> list | dict:
    # Rewrite legacy URLs to the new router endpoint
    if url.startswith(HF_LEGACY_URL):
        model_path = url[len(HF_LEGACY_URL):]
        url = HF_ROUTER_URL + model_path

    headers = {"Authorization": f"Bearer {token}"}
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff_base ** attempt)
            continue
        if attempt < retries - 1:
            time.sleep(backoff_base ** attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"HF API failed after {retries} attempts: {resp.status_code} {resp.text[:200]}")
