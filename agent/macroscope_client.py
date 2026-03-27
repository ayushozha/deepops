"""
Macroscope API client wrapper for codebase understanding queries.

Provides a clean interface for querying the Macroscope codebase analysis API,
with retry logic, fallback fixtures for demo/evaluation mode, and typed
exceptions for callers to handle.
"""

import json
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MacroscopeError(Exception):
    """Base exception for all Macroscope client errors."""


class MacroscopeConfigError(MacroscopeError):
    """Raised when the client is misconfigured (e.g. missing API key)."""


class MacroscopeAPIError(MacroscopeError):
    """Raised when the Macroscope API returns a non-200 response."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Macroscope API error {status_code}: {detail}")


# ---------------------------------------------------------------------------
# Fallback fixtures
# ---------------------------------------------------------------------------

_FALLBACK_FIXTURES: dict[str, str] = {
    "calculate_zero_division": (
        "The `calculate(a, b)` function in demo-app/main.py performs integer "
        "division (`a // b`) using path parameters received from the GET "
        "/calculate/{a}/{b} endpoint. There is no validation or guard against "
        "`b == 0`. When the route /calculate/0 is hit (i.e. b=0), Python "
        "raises `ZeroDivisionError: division by zero`. The function has no "
        "downstream writes or side-effects; it is a pure computation that "
        "returns the result directly in the HTTP response. No other endpoints "
        "call this function. The fix is to validate that b != 0 before "
        "performing the division and return an appropriate HTTP 400 error."
    ),
    "user_key_error": (
        "The GET /user/{username} endpoint in demo-app/main.py looks up a "
        "user from an in-memory `users` dict via `users.get(username)`. When "
        "the username is not found, `.get()` returns `None`. The code then "
        "immediately accesses `['name']` on the result without a None check, "
        "causing `KeyError: 'name'`. This is a high-severity issue because "
        "any unauthenticated caller can trigger a 500 by requesting a "
        "non-existent username. The user dict is populated at startup and is "
        "not modified at runtime. Callers include the frontend profile page "
        "and the /admin/users list endpoint which iterates all known users. "
        "The fix is to check for None and return HTTP 404 when the user is "
        "not found."
    ),
    "search_timeout": (
        "The GET /search endpoint in demo-app/main.py contains a blocking "
        "`time.sleep(5)` call inside an async request handler. This blocks "
        "the entire event loop for 5 seconds, preventing all other concurrent "
        "requests from being processed. Under any meaningful load this causes "
        "cascading timeouts across the service. The search function queries "
        "an external search index; the sleep was likely added as a placeholder "
        "or naive rate-limit. Downstream dependencies include the search "
        "index client and the response serializer. The fix is to replace "
        "`time.sleep(5)` with `await asyncio.sleep(5)` (if the delay is "
        "intentional) or remove it entirely, and ensure the external call "
        "uses an async HTTP client. This is critical severity because it "
        "degrades the entire service, not just the /search endpoint."
    ),
}

# Keywords used to match a question to the correct fallback fixture
_FALLBACK_KEYWORDS: list[tuple[list[str], str]] = [
    (["calculate", "division", "zero"], "calculate_zero_division"),
    (["user", "key", "lookup", "name"], "user_key_error"),
    (["search", "timeout", "sleep", "blocking"], "search_timeout"),
]


def _match_fallback(question: str, incident_context: dict | None = None) -> str:
    """Return the best-matching fallback fixture for a question string."""
    text = question.lower()
    if incident_context:
        text += " " + json.dumps(incident_context).lower()

    best_key: str | None = None
    best_score = 0
    for keywords, key in _FALLBACK_KEYWORDS:
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key and best_score > 0:
        return _FALLBACK_FIXTURES[best_key]

    return (
        "No matching codebase context found for the given question. "
        "The Macroscope API did not return relevant results."
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class MacroscopeClient:
    """Wrapper around the Macroscope codebase understanding API.

    Parameters
    ----------
    api_key:
        Macroscope API key. Falls back to the ``MACROSCOPE_WEBHOOK_API``
        environment variable when *None*.
    base_url:
        Root URL of the Macroscope API.
    fallback_mode:
        When *True*, skip real API calls entirely and return deterministic
        fixture responses. Also used automatically when the API is
        unreachable.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.macroscope.com",
        fallback_mode: bool = False,
    ) -> None:
        self.api_key = api_key or os.environ.get("MACROSCOPE_WEBHOOK_API")
        self.base_url = base_url.rstrip("/")
        self.fallback_mode = fallback_mode
        self._timeout = 10  # seconds
        self._max_retries = 2
        self._backoff_base = 1.0  # seconds

        if not self.fallback_mode and not self.api_key:
            raise MacroscopeConfigError(
                "No API key provided and MACROSCOPE_WEBHOOK_API is not set. "
                "Pass api_key= or set the environment variable, or use "
                "fallback_mode=True for offline/demo operation."
            )

    # ------------------------------------------------------------------
    # Core query method
    # ------------------------------------------------------------------

    def query(
        self,
        repo_id: str,
        question: str,
        incident_context: dict | None = None,
    ) -> str:
        """Ask Macroscope a question about a repository.

        Parameters
        ----------
        repo_id:
            Identifier of the repository in Macroscope.
        question:
            Natural-language question about the codebase.
        incident_context:
            Optional dict with incident metadata (error type, path, etc.)
            to give Macroscope additional signal.

        Returns
        -------
        str
            Clean text context suitable for downstream reasoning.

        Raises
        ------
        MacroscopeConfigError
            If the API key is missing.
        MacroscopeAPIError
            If the API returns a non-200 status after retries.
        """
        if self.fallback_mode:
            logger.debug("Fallback mode active; returning fixture response.")
            return _match_fallback(question, incident_context)

        payload: dict = {
            "repo_id": repo_id,
            "question": question,
        }
        if incident_context:
            payload["context"] = incident_context

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1 + self._max_retries):
            if attempt > 0:
                wait = self._backoff_base * (2 ** (attempt - 1))
                logger.info(
                    "Retry %d/%d after %.1fs backoff",
                    attempt,
                    self._max_retries,
                    wait,
                )
                time.sleep(wait)

            try:
                resp = requests.post(
                    f"{self.base_url}/v1/query",
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                logger.warning("Request failed (attempt %d): %s", attempt + 1, exc)
                last_error = exc
                continue

            if resp.status_code == 200:
                body = resp.json()
                answer = body.get("answer", "").strip()
                if not answer:
                    logger.warning("Macroscope returned empty answer; using fallback.")
                    return _match_fallback(question, incident_context)
                return answer

            # Retriable server errors
            if resp.status_code >= 500:
                logger.warning(
                    "Server error %d (attempt %d): %s",
                    resp.status_code,
                    attempt + 1,
                    resp.text[:200],
                )
                last_error = MacroscopeAPIError(resp.status_code, resp.text[:200])
                continue

            # Non-retriable client errors
            raise MacroscopeAPIError(resp.status_code, resp.text[:500])

        # All retries exhausted -- fall back gracefully
        logger.error(
            "All %d attempts failed. Falling back to fixture response. "
            "Last error: %s",
            1 + self._max_retries,
            last_error,
        )
        return _match_fallback(question, incident_context)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def ask_about_function(
        self, repo_id: str, file_path: str, function_name: str
    ) -> str:
        """Ask what a specific function does and what calls it."""
        question = (
            f"What does the function `{function_name}` in `{file_path}` do? "
            f"What are its inputs, outputs, and side-effects? "
            f"What other functions or endpoints call it?"
        )
        return self.query(repo_id, question)

    def ask_about_callers(
        self, repo_id: str, file_path: str, function_name: str
    ) -> str:
        """Ask who calls a specific function and how."""
        question = (
            f"List all callers of `{function_name}` in `{file_path}`. "
            f"For each caller, describe how it uses the return value "
            f"and whether it handles errors from this function."
        )
        return self.query(repo_id, question)

    def ask_about_dependencies(self, repo_id: str, file_path: str) -> str:
        """Ask about the imports and dependencies of a file."""
        question = (
            f"What are the external and internal dependencies of `{file_path}`? "
            f"List every import, the modules they come from, and which "
            f"functions in this file use each dependency."
        )
        return self.query(repo_id, question)
