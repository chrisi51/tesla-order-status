"""Utility helpers for HTTP requests with retry logic."""

import json as jsonlib
import time
import requests
from typing import Dict, Union

from app.utils.helpers import exit_with_status
from app.utils.locale import t

def request_with_retry(url, headers=None, data=None, json=None, max_retries=3, exit_on_error=True):
    """Perform a GET or POST request with exponential backoff retries.

    Parameters
    ----------
    url : str
        Target endpoint.
    headers : dict, optional
        Headers to include with the request.
    data : Any, optional
        Data payload for ``POST`` requests.
    json : Any, optional
        JSON payload for ``POST`` requests.
    max_retries : int
        Number of attempts before giving up.
    exit_on_error : bool
        When ``True`` (default) the function prints a user friendly message
        and terminates the program on failure. When ``False`` a ``RuntimeError``
        is raised instead so callers can handle network issues gracefully.
    """
    _STATUS_TEXTS: Dict[Union[int, str], str] = {
        400: t("400"),
        401: t("401"),
        403: t("403"),
        404: t("404"),
        422: t("422"),
        429: t("429"),
        '5xx': t("5xx"),
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
                        if exit_on_error:
                            exit_with_status(_STATUS_TEXTS['5xx'])
                        else:
                            raise RuntimeError(_STATUS_TEXTS['5xx'])

                    time.sleep(5 ** attempt)
                    continue
                else:
                    error_text = _STATUS_TEXTS.get(response.status_code, _STATUS_TEXTS['5xx'])
                    if exit_on_error:
                        exit_with_status(error_text)
                    else:
                        raise RuntimeError(error_text)

            return response
        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                if exit_on_error:
                    exit_with_status(_STATUS_TEXTS['5xx'])
                else:
                    raise RuntimeError(_STATUS_TEXTS['5xx'])
            time.sleep(2 ** attempt)
    return None
