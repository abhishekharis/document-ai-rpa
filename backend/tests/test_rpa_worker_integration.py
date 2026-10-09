"""Runs the real Python RPA processor and simulated accounting app against the API on a disposable database.

Flask is only installed in the accounting app's venv, so this test is skipped unless it is importable, e.g.:
PYTHONPATH=../simulated-accounting-app/venv/lib/python3.12/site-packages pytest tests/test_rpa_worker_integration.py
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

from tests.conftest import TEST_RPA_API_KEY
from tests.test_api import approve, audit_events, seed_invoice

pytest.importorskip("flask")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FlaskSession:
    """Lets the RPA processor's requests-style accounting calls reach the Flask app in-process."""

    def __init__(self, flask_client):
        self.flask_client = flask_client

    def post(self, url, json):
        response = self.flask_client.post(urlsplit(url).path, json=json)
        return SimpleNamespace(status_code=response.status_code, json=response.get_json)


def test_worker_enters_manually_approved_invoice_into_accounting(client, mongo):
    accounting = load_module("simulated_accounting_app", PROJECT_ROOT / "simulated-accounting-app" / "app.py")
    rpa = load_module("python_rpa_processor", PROJECT_ROOT / "rpa" / "python_rpa_processor.py")
    accounting.accounting_records.clear()

    processor = rpa.RPAProcessor("http://testserver", TEST_RPA_API_KEY, "http://accounting.test")
    processor.api_session = client
    processor.accounting_session = FlaskSession(accounting.app.test_client())

    document_id = seed_invoice(mongo)
    assert approve(client, document_id).json()["status"] == "RPA_QUEUED"

    queue = processor.get_rpa_queue()
    assert queue["count"] == 1
    assert processor.process_invoice(document_id, queue["invoices"][0]) is True

    assert len(accounting.accounting_records) == 1
    record = accounting.accounting_records[0]
    assert record["invoice_number"] == "INV-1001"
    assert record["vendor"] == "Acme Supplies"
    assert record["total"] == 108.0

    doc = mongo.invoices.find_one({"document_id": document_id})
    assert doc["status"] == "RPA_COMPLETED"
    assert record["accounting_id"] in doc["rpa"]["message"]
    assert audit_events(mongo, document_id) == ["APPROVED", "RPA_QUEUED", "RPA_STARTED", "RPA_COMPLETED"]
    assert processor.get_rpa_queue()["count"] == 0
