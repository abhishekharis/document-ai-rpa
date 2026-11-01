"""End-to-end smoke test against a running full stack (docker-compose.full.yml).

Usage: smoke_full_stack.py [BASE_URL]   (default http://localhost:8080)

Uploads a generated invoice, approves it if it needs review, waits for the RPA
worker to complete it, and checks the record appears in the accounting app.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
HERE = os.path.dirname(os.path.abspath(__file__))


def request(method, path, body=None, headers=None, timeout=300):
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read() or b"null")


def wait_for(description, check, timeout, interval=3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = check()
        if result:
            return result
        time.sleep(interval)
    fail(f"Timed out waiting for {description}")


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def healthy():
    try:
        return request("GET", "/api/health", timeout=5).get("status") == "healthy"
    except (urllib.error.URLError, OSError, ValueError):
        return False


def upload(pdf_path):
    boundary = uuid.uuid4().hex
    with open(pdf_path, "rb") as f:
        content = f.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"sample_invoice.pdf\"\r\nContent-Type: application/pdf\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    return request("POST", "/api/invoices/upload", body,
                   {"Content-Type": f"multipart/form-data; boundary={boundary}"})


def main():
    wait_for("backend health", healthy, timeout=180)
    print("ok: stack is healthy")

    with tempfile.TemporaryDirectory() as tmp:
        pdf = os.path.join(tmp, "sample_invoice.pdf")
        subprocess.run([sys.executable, os.path.join(HERE, "make_sample_invoice.py"), pdf], check=True)
        document_id = upload(pdf)["document_id"]
    print(f"ok: uploaded {document_id}")

    def processed():
        invoice = request("GET", f"/api/invoices/{document_id}")
        return invoice if invoice["status"] not in ("UPLOADED", "PROCESSING") else None

    invoice = wait_for("OCR processing", processed, timeout=300)
    print(f"ok: processed -> {invoice['status']}")
    if invoice["status"] == "NEEDS_REVIEW":
        body = json.dumps({"document_id": document_id, "reviewed_by": "smoke-test"}).encode()
        request("POST", f"/api/invoices/{document_id}/approve", body, {"Content-Type": "application/json"})
        print("ok: approved manually")
    elif invoice["status"] in ("ERROR", "REJECTED"):
        fail(f"invoice ended as {invoice['status']}")

    def rpa_done():
        current = request("GET", f"/api/invoices/{document_id}")
        if current["status"] in ("RPA_FAILED", "ERROR", "REJECTED"):
            fail(f"invoice ended as {current['status']}: {current.get('rpa')}")
        return current if current["status"] == "RPA_COMPLETED" else None

    invoice = wait_for("RPA completion", rpa_done, timeout=180)
    accounting_id = (invoice.get("rpa") or {}).get("accounting_record_id")
    if not accounting_id:
        fail("RPA completed but no accounting_record_id was stored")
    print(f"ok: RPA completed -> {accounting_id}")

    records = request("GET", "/accounting/api/records")["records"]
    match = [r for r in records if r["accounting_id"] == accounting_id]
    if not match or match[0]["external_reference"] != document_id:
        fail(f"{accounting_id} not found in accounting app with reference {document_id}")
    print("ok: record present in the accounting app")

    with urllib.request.urlopen(BASE + "/accounting/", timeout=10) as page:
        html = page.read().decode()
    if 'href="/accounting/new-invoice"' not in html:
        fail("accounting pages do not carry the /accounting prefix")
    print("ok: accounting pages are prefix-aware")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
