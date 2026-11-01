import os
import sys
from unittest.mock import MagicMock

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from python_rpa_processor import RPAProcessor  # noqa: E402

INVOICE = {
    "document_id": "DOC-1",
    "vendor": {"name": "ACME"},
    "invoice_number": "INV-1",
    "invoice_date": "2026-10-01",
    "currency": "USD",
    "total": 108.0,
}


def response(payload, status=200):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = payload
    mock.raise_for_status.side_effect = (
        None if status < 400 else requests.HTTPError(f"{status}")
    )
    return mock


@pytest.fixture
def processor():
    proc = RPAProcessor("http://api", "key", "http://acct")
    proc.api_session = MagicMock()
    proc.accounting_session = MagicMock()
    return proc


def test_success_reports_accounting_id_and_sends_reference(processor):
    processor.api_session.post.return_value = response({"status": "PROCESSING"})
    processor.accounting_session.post.return_value = response(
        {"success": True, "accounting_id": "ACC-1"}
    )

    assert processor.process_invoice("DOC-1", INVOICE) is True

    submitted = processor.accounting_session.post.call_args.kwargs["json"]
    assert submitted["external_reference"] == "DOC-1"
    result_call = processor.api_session.post.call_args_list[-1]
    assert result_call.kwargs["json"]["success"] is True
    assert result_call.kwargs["json"]["accounting_record_id"] == "ACC-1"


def test_accounting_failure_reports_failure(processor):
    processor.api_session.post.return_value = response({"status": "PROCESSING"})
    processor.accounting_session.post.return_value = response({"success": False}, status=400)

    assert processor.process_invoice("DOC-1", INVOICE) is False
    assert processor.api_session.post.call_args_list[-1].kwargs["json"]["success"] is False


def test_start_failure_skips_accounting(processor):
    processor.api_session.post.side_effect = [response({}, status=409), response({})]

    assert processor.process_invoice("DOC-1", INVOICE) is False
    processor.accounting_session.post.assert_not_called()


def test_queue_drains_all_invoices(processor):
    processor.api_session.get.return_value = response(
        {"invoices": [{**INVOICE, "document_id": f"DOC-{i}"} for i in range(3)], "count": 3}
    )
    processor.process_invoice = MagicMock(return_value=True)

    assert processor.process_queue_once() == 3
    assert processor.process_invoice.call_count == 3


def test_stop_halts_queue_processing(processor):
    processor.api_session.get.return_value = response(
        {"invoices": [INVOICE, {**INVOICE, "document_id": "DOC-2"}], "count": 2}
    )
    processor.process_invoice = MagicMock(side_effect=lambda *_: processor.stop())

    processor.process_queue_once()
    assert processor.process_invoice.call_count == 1


def test_unreachable_backend_returns_empty_queue(processor):
    processor.api_session.get.side_effect = requests.ConnectionError("down")
    assert processor.process_queue_once() == 0
