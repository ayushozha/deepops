"""Tests for the Macroscope API client."""

import pytest
from unittest.mock import patch, MagicMock

from agent.macroscope_client import (
    MacroscopeClient,
    MacroscopeConfigError,
    MacroscopeAPIError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_QUERIES = [
    {
        "question": "What does the calculate function do with division by zero?",
        "incident_context": {"error_type": "ZeroDivisionError", "function": "calculate"},
    },
    {
        "question": "What does the user lookup do when the key name is missing?",
        "incident_context": {"error_type": "KeyError", "function": "get_user"},
    },
    {
        "question": "Why does the search endpoint timeout with blocking sleep?",
        "incident_context": {"error_type": "TimeoutError", "function": "search"},
    },
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFallbackMode:
    """Test that fallback mode returns canned context without hitting an API."""

    @pytest.mark.parametrize("query_info", DEMO_QUERIES)
    def test_fallback_mode_returns_context(self, query_info):
        client = MacroscopeClient(fallback_mode=True)
        result = client.query(
            repo_id="deepops-demo-app",
            question=query_info["question"],
            incident_context=query_info["incident_context"],
        )
        assert isinstance(result, str)
        assert len(result) > 0, "Fallback context must be non-empty"


class TestConfigErrors:
    """Test that missing configuration raises the right error."""

    def test_missing_api_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure MACROSCOPE_WEBHOOK_API is not set
            import os
            env = os.environ.copy()
            env.pop("MACROSCOPE_WEBHOOK_API", None)
            with patch.dict("os.environ", env, clear=True):
                with pytest.raises(MacroscopeConfigError):
                    client = MacroscopeClient(fallback_mode=False)
                    client.query("repo", "question")


class TestHelperMethods:
    """Test that helper methods delegate to query()."""

    def test_helper_methods_use_query(self):
        client = MacroscopeClient(fallback_mode=True)
        with patch.object(client, "query", return_value="mocked context") as mock_query:
            result = client.ask_about_function(
                repo_id="deepops-demo-app",
                file_path="demo-app/main.py",
                function_name="calculate",
            )
            mock_query.assert_called_once()
            call_args = mock_query.call_args
            # First positional arg is repo_id
            assert call_args[0][0] == "deepops-demo-app"
            # Second positional arg is the question string
            question = call_args[0][1]
            assert isinstance(question, str)
            assert "calculate" in question
            assert result == "mocked context"


class TestFallbackOnAPIError:
    """Test that API errors trigger fallback instead of raising."""

    def test_fallback_on_api_error(self):
        client = MacroscopeClient(api_key="test-key", fallback_mode=False)
        # Force fallback_mode off so it tries the real API
        import requests

        with patch("agent.macroscope_client.requests.post") as mock_post:
            mock_post.side_effect = requests.ConnectionError("Connection refused")
            # After exhausting retries, the client should fall back gracefully
            result = client.query(
                repo_id="deepops-demo-app",
                question="What does the calculate function do with division by zero?",
                incident_context={"error_type": "ZeroDivisionError"},
            )
            assert isinstance(result, str)
            assert len(result) > 0, "Should return fallback context, not raise"

        # Verify it actually tried to make API calls
        assert mock_post.call_count >= 1
