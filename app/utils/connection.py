"""Utility helpers for HTTP requests with retry logic."""

import json as jsonlib
import time
import requests
from curl_cffi import requests as tls_requests
from typing import Dict, Union

from app.utils.helpers import exit_with_status
from app.utils.locale import t

def request_with_retry(url, headers=None, data=None, json=None, max_retries=3, exit_on_error=True, impersonate=None):
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
    # Tesla's auth edge fingerprints the TLS handshake of the token request: a
    # plain OpenSSL handshake yields a token that owner-api rejects with 403.
    http = tls_requests if impersonate else requests
    kw = {'impersonate': impersonate} if impersonate else {}

    for attempt in range(max_retries):
        try:
            if data is None and json is None:
                response = http.get(url, headers=headers, **kw)
            else:
                if json is not None:
                    response = http.post(url, headers=headers, json=json, **kw)
                else:
                    # Falls string/bytes: direkt senden; falls dict: sauber als JSON senden
                    if isinstance(data, (dict, list)):
                        response = http.post(
                            url,
                            headers={"Content-Type": "application/json", **(headers or {})},
                            data=jsonlib.dumps(data, separators=(",", ":")),
                            **kw,
                        )
                    else:
                        response = http.post(url, headers=headers, data=data, **kw)

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
