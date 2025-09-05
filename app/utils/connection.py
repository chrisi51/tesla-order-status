"""Utility helpers for HTTP requests with retry logic."""

import json as jsonlib
import time
import requests
from typing import Dict

from app.utils.helpers import exit_with_status

def request_with_retry(url, headers=None, data=None, json=None, max_retries=3):
    """Perform a GET or POST request with exponential backoff retries."""

    _STATUS_TEXTS: Dict[int | str, str] = {
        400: "Invalid request (400): Please check parameters.",
        401: "Unauthorized (401): Token/login seems incorrect.",
        403: "Forbidden (403): Data not accessible. Try again later.",
        404: "Not found (404): Resource does not exist or is not visible.",
        422: "Unprocessable Entity (422): Invalid/missing fields in request.",
        429: "Too Many Requests (429): Rate limit reached. Please wait and try again.",
        '5xx': "API unreachable - please try again later.",
    }
    for attempt in range(max_retries):
        try:
            if data is None and json is None:
                response = requests.get(url, headers=headers)
            else:
                if json is not None:
                    response = requests.post(url, headers=headers, json=json)
                else:
                    # Falls string/bytes: direkt senden; falls dict: sauber als JSON senden
                    if isinstance(data, (dict, list)):
                        response = requests.post(
                            url,
                            headers={"Content-Type": "application/json", **(headers or {})},
                            data=jsonlib.dumps(data, separators=(",", ":")),
                        )
                    else:
                        response = requests.post(url, headers=headers, data=data)

            try:
                response.raise_for_status()
            except Exception:
                if response.status_code >= 500:
                    if attempt == max_retries - 1:
                        exit_with_status(_STATUS_TEXTS['5xx'])
                    time.sleep(5 ** attempt)
                    continue
                else:
                    error_text = _STATUS_TEXTS.get(response.status_code, _STATUS_TEXTS['5xx'])
                    exit_with_status(error_text)

            return response
        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                exit_with_status(_STATUS_TEXTS['5xx'])
            time.sleep(2 ** attempt)
