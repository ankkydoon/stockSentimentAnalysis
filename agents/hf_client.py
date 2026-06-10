import time
import requests

# HuggingFace Inference API — try new router URL first, fall back to legacy
HF_ROUTER_URL = "https://router.huggingface.co/hf-inference/models"
HF_LEGACY_URL = "https://api-inference.huggingface.co/models"


def hf_chat(model_id: str, prompt: str, token: str, max_tokens: int = 150,
            retries: int = 3, backoff_base: float = 2.0) -> str:
    """Call HuggingFace chat completions endpoint. Returns the assistant reply text."""
    url = f"{HF_ROUTER_URL}/{model_id}/v1/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    headers = {"Authorization": f"Bearer {token}"}
    last_exc: Exception | None = None
    resp = None
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff_base ** attempt)
            continue
        if attempt < retries - 1:
            time.sleep(backoff_base ** attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError(
        f"HF API failed after {retries} attempts: {resp.status_code} {resp.text[:200]}"
    )


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
