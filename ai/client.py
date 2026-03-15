"""
Gemini client — free tier wrapper with rate limiting and retry.
No external SDK needed — uses the REST API directly via requests.

Free tier limits (per model):
  gemini-2.5-flash:    10 RPM, 500 RPD, 1M TPD
  gemini-2.0-flash:    15 RPM, 1500 RPD, 1M TPD
  gemini-2.0-flash-lite: 30 RPM, 1500 RPD, 1M TPD

We try models in order from lowest to highest quota consumption.
"""
import os
import json
import time
import requests

_last_call_time = 0.0

# Model priority order — lite models have highest free RPM
MODEL_FALLBACK_ORDER = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
]


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise ValueError(
            "GEMINI_API_KEY not set. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    return key


def _post(model: str, prompt: str, api_key: str) -> requests.Response:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
        f":generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
            "maxOutputTokens": 2048,
        },
    }
    return requests.post(url, json=payload, timeout=30)


def generate(prompt: str, model: str = "", rate_limit_seconds: float = 7.0) -> dict:
    """
    Send a prompt to Gemini and return parsed JSON response.
    Auto-falls back through models on 429. Returns empty dict on failure.
    """
    global _last_call_time

    api_key = _get_api_key()

    # Rate limiting
    elapsed = time.time() - _last_call_time
    if elapsed < rate_limit_seconds:
        time.sleep(rate_limit_seconds - elapsed)

    # Build model list to try
    if model:
        models_to_try = [model] + [m for m in MODEL_FALLBACK_ORDER if m != model]
    else:
        models_to_try = MODEL_FALLBACK_ORDER

    _last_call_time = time.time()

    for attempt_model in models_to_try:
        try:
            resp = _post(attempt_model, prompt, api_key)

            if resp.status_code == 200:
                if attempt_model != (model or models_to_try[0]):
                    print(f"[gemini] Using fallback model: {attempt_model}")
                return _parse_response(resp)

            if resp.status_code == 429:
                print(f"[gemini] {attempt_model} quota exceeded, trying next model...")
                time.sleep(2)
                continue

            if resp.status_code == 404:
                # Model not available on this key
                continue

            print(f"[gemini] API error {resp.status_code}: {resp.text[:150]}")
            return {}

        except requests.RequestException as e:
            print(f"[gemini] Request error: {e}")
            return {}

    print("[gemini] All models exhausted — quota exceeded on all fallbacks")
    return {}


def _parse_response(resp: requests.Response) -> dict:
    """Extract and parse JSON from a successful Gemini response."""
    try:
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not text:
            return {}

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

        return json.loads(text)

    except json.JSONDecodeError as e:
        print(f"[gemini] JSON parse error: {e}")
        return {}
