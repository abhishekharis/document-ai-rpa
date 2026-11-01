from app import create_app

INVOICE = {
    "vendor": "ACME Office Supplies",
    "invoice_number": "INV-1001",
    "invoice_date": "2026-10-01",
    "due_date": "2026-10-31",
    "currency": "USD",
    "subtotal": 100.0,
    "tax": 8.0,
    "total": 108.0,
}


def test_create_via_json_and_list(client):
    response = client.post("/new-invoice", json=INVOICE)
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["accounting_id"].startswith("ACC-")

    records = client.get("/api/records").get_json()
    assert records["count"] == 1
    assert records["records"][0]["vendor"] == "ACME Office Supplies"
    assert records["records"][0]["total"] == 108.0


def test_create_via_form_shows_success_page(client):
    response = client.post("/new-invoice", data={**INVOICE, "line_items": "Paper"})
    assert response.status_code == 200
    assert b"ACC-" in response.data
    assert client.get("/api/records").get_json()["count"] == 1


def test_records_survive_app_restart(db_path):
    first = create_app(db_path).test_client()
    accounting_id = first.post("/new-invoice", json=INVOICE).get_json()["accounting_id"]

    second = create_app(db_path).test_client()
    records = second.get("/api/records").get_json()["records"]
    assert [r["accounting_id"] for r in records] == [accounting_id]


def test_same_external_reference_does_not_create_duplicate(client):
    payload = {**INVOICE, "external_reference": "DOC-123"}
    first = client.post("/new-invoice", json=payload).get_json()
    second = client.post("/new-invoice", json=payload).get_json()

    assert second["duplicate"] is True
    assert second["accounting_id"] == first["accounting_id"]
    assert client.get("/api/records").get_json()["count"] == 1


def test_invalid_amount_returns_400_for_json(client):
    response = client.post("/new-invoice", json={**INVOICE, "total": "not-a-number"})
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert client.get("/api/records").get_json()["count"] == 0


def test_view_record_and_missing_record(client):
    accounting_id = client.post("/new-invoice", json=INVOICE).get_json()["accounting_id"]
    assert client.get(f"/record/{accounting_id}").status_code == 200
    assert client.get("/record/ACC-MISSING").status_code == 302


def test_links_use_forwarded_prefix(client):
    client.post("/new-invoice", json=INVOICE)
    page = client.get("/", headers={"X-Forwarded-Prefix": "/accounting"}).get_data(as_text=True)
    assert 'href="/accounting/new-invoice"' in page
    assert 'href="/accounting/record/ACC-' in page


def test_links_without_prefix_are_root_relative(client):
    page = client.get("/").get_data(as_text=True)
    assert 'href="/new-invoice"' in page
