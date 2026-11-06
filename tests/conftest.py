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
def isolate_license_log_file(tmp_path, monkeypatch):
    """
    Ensures tests never pollute or overwrite the real output/stock_license_log.json.
    Points StockLicenseManager default path to an isolated temp file.
    """
    from app.stock.license_log import StockLicenseManager
    temp_log = str(tmp_path / "temp_stock_license_log.json")
    def _mock_init(self, log_path=temp_log):
        self.log_path = log_path
        self._used_ids_cache = None
    monkeypatch.setattr(StockLicenseManager, "__init__", _mock_init)


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
