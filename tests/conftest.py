import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def isolate_daily_job_file(tmp_path, monkeypatch):
    """
    Ensures tests never touch or overwrite the real daily_job.json.
    Points DailyJobManager default path to an isolated temp file.
    """
    from app.jobs.manager import DailyJobManager
    temp_state = str(tmp_path / "temp_daily_job.json")
    monkeypatch.setattr(DailyJobManager, "__init__", lambda self, state_file_path=temp_state: setattr(self, "state_file_path", state_file_path))


@pytest.fixture(autouse=True)
def block_network_calls(monkeypatch):
    """
    Global fixture blocking real HTTP network calls during test execution.
    Raises RuntimeError if any unmocked HTTP call is attempted.
    """
    def raise_network_error(*args, **kwargs):
        raise RuntimeError("Blocked real network call during test execution!")

    # Block httpx
    try:
        import httpx
        monkeypatch.setattr(httpx.Client, "send", raise_network_error)
        monkeypatch.setattr(httpx.AsyncClient, "send", raise_network_error)
    except ImportError:
        pass

    # Block requests
    try:
        import requests
        monkeypatch.setattr(requests.sessions.Session, "send", raise_network_error)
    except ImportError:
        pass

    # Block urllib.request.urlopen
    try:
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", raise_network_error)
    except (ImportError, AttributeError):
        pass

