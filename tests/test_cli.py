"""Smoke tests for cli.py — run subcommands as subprocesses."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cli.py"
SAMPLE_JSON = PROJECT_ROOT / "sample_invoice.json"


def _write_credit_note_json(tmp_path: Path) -> Path:
    """Derive a credit-note JSON from sample_invoice.json (drop DueDate, add CN fields)."""
    data = json.loads(SAMPLE_JSON.read_text())
    data.pop("invoice_type_code", None)
    data.pop("due_date", None)
    data["credit_note_type_code"] = "381"
    data["invoice_number"] = "CN-0001"
    data["billing_reference"] = {"id": "INV-0001", "issue_date": "2025-01-15"}
    path = tmp_path / "sample_credit_note.json"
    path.write_text(json.dumps(data))
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


def test_create_produces_xml(tmp_path: Path) -> None:
    out_file = tmp_path / "invoice.xml"
    result = _run("create", "--input", str(SAMPLE_JSON), "--out", str(out_file))
    assert result.returncode == 0
    assert "Generated UBL invoice" in result.stdout
    assert out_file.exists()
    content = out_file.read_bytes()
    assert b"Invoice" in content


def test_create_embeds_pdf_by_default(tmp_path: Path) -> None:
    out_file = tmp_path / "invoice.xml"
    result = _run("create", "--input", str(SAMPLE_JSON), "--out", str(out_file))
    assert result.returncode == 0
    content = out_file.read_bytes()
    assert b"AdditionalDocumentReference" in content
    assert b"application/pdf" in content


def test_create_no_pdf_flag_omits_embedding(tmp_path: Path) -> None:
    out_file = tmp_path / "invoice.xml"
    result = _run("create", "--input", str(SAMPLE_JSON), "--out", str(out_file), "--no-pdf")
    assert result.returncode == 0
    content = out_file.read_bytes()
    assert b"AdditionalDocumentReference" not in content


def test_validate_ok(tmp_path: Path) -> None:
    out_file = tmp_path / "invoice.xml"
    _run("create", "--input", str(SAMPLE_JSON), "--out", str(out_file))

    result = _run("validate", "--file", str(out_file))
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_validate_invalid_xml(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.xml"
    bad_file.write_text("<not-an-invoice/>")

    result = _run("validate", "--file", str(bad_file))
    assert result.returncode == 0  # CLI prints rules but doesn't exit non-zero
    assert "FATAL" in result.stdout


def test_send_rejects_xsd_invalid_xml(tmp_path: Path) -> None:
    """cmd_send should reject XML that fails XSD validation."""
    bad_file = tmp_path / "bad.xml"
    bad_file.write_text("<not-an-invoice/>")

    result = subprocess.run(
        [sys.executable, str(CLI), "send", "--file", str(bad_file), "--recipient", "9908:test"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={
            **__import__("os").environ,
            "PEPPYRUS_API_KEY": "test-key",
            "PEPPOL_SENDER_ID": "9925:test",
        },
    )
    assert result.returncode == 0
    assert "FATAL" in result.stdout
    assert "abort" in result.stdout.lower()


def test_report_missing_credentials() -> None:
    result = subprocess.run(
        [sys.executable, str(CLI), "report", "--id", "fake-id"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={**__import__("os").environ, "PEPPYRUS_API_KEY": ""},
    )
    assert result.returncode == 0
    assert "Missing PEPPYRUS_API_KEY" in result.stdout


# --- Credit note subcommand coverage ---


def test_create_type_credit_note_produces_credit_note(tmp_path: Path) -> None:
    cn_json = _write_credit_note_json(tmp_path)
    out_file = tmp_path / "cn.xml"
    result = _run("create", "--type", "credit-note", "--input", str(cn_json), "--out", str(out_file), "--no-pdf")
    assert result.returncode == 0, result.stderr
    assert "credit note" in result.stdout
    assert out_file.exists()
    content = out_file.read_bytes()
    assert b"<CreditNote" in content
    assert b"CreditNoteTypeCode" in content
    assert b"CreditNoteLine" in content
    assert b"CreditedQuantity" in content
    assert b"BillingReference" in content
    assert b"InvoiceTypeCode" not in content


def test_create_default_type_still_produces_invoice(tmp_path: Path) -> None:
    # Regression: omitting --type should still produce an invoice.
    out_file = tmp_path / "inv.xml"
    result = _run("create", "--input", str(SAMPLE_JSON), "--out", str(out_file), "--no-pdf")
    assert result.returncode == 0
    content = out_file.read_bytes()
    assert b"<Invoice" in content
    assert b"CreditNote" not in content


def test_validate_credit_note(tmp_path: Path) -> None:
    cn_json = _write_credit_note_json(tmp_path)
    out_file = tmp_path / "cn.xml"
    _run("create", "--type", "credit-note", "--input", str(cn_json), "--out", str(out_file), "--no-pdf")
    result = _run("validate", "--file", str(out_file))
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_send_unknown_root_rejected(tmp_path: Path) -> None:
    # Plain <Foo/> should trip LOCAL-UNKNOWN-ROOT and abort.
    bad_file = tmp_path / "bad.xml"
    bad_file.write_text('<?xml version="1.0"?><Foo xmlns="urn:x"/>')
    result = subprocess.run(
        [sys.executable, str(CLI), "send", "--file", str(bad_file), "--recipient", "9908:test"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={
            **__import__("os").environ,
            "PEPPYRUS_API_KEY": "test-key",
            "PEPPOL_SENDER_ID": "9925:test",
        },
    )
    assert result.returncode == 0
    assert "LOCAL-UNKNOWN-ROOT" in result.stdout
    assert "abort" in result.stdout.lower()


# --- Unit tests: cli module functions with mocked HTTP ---


def test_detect_document_type_invoice() -> None:
    import cli

    assert cli._detect_document_type(b'<?xml version="1.0"?><Invoice xmlns="urn:x"/>') == "invoice"


def test_detect_document_type_credit_note() -> None:
    import cli

    assert cli._detect_document_type(b'<?xml version="1.0"?><CreditNote xmlns="urn:x"/>') == "credit-note"


def test_detect_document_type_raises_on_unknown() -> None:
    import cli

    with pytest.raises(ValueError, match="Unknown document root"):
        cli._detect_document_type(b'<?xml version="1.0"?><Foo xmlns="urn:x"/>')


def test_cmd_send_auto_detects_credit_note_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Build a real valid credit note XML, then intercept the HTTP call to
    # verify that package_message was called with CREDIT_NOTE_DOCUMENT_TYPE.
    import cli
    from peppol_sender.api import CREDIT_NOTE_DOCUMENT_TYPE
    from peppol_sender.ubl import generate_credit_note

    cn_data = {
        "invoice_number": "CN-X",
        "issue_date": "2025-02-01",
        "credit_note_type_code": "381",
        "currency": "EUR",
        "seller": {
            "name": "S",
            "registration_name": "S BV",
            "endpoint_id": "BE0123456789",
            "endpoint_scheme": "0208",
            "country": "BE",
        },
        "buyer": {
            "name": "B",
            "registration_name": "B BV",
            "endpoint_id": "NL987654321",
            "endpoint_scheme": "0208",
            "country": "NL",
        },
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.0, "tax_category": "E", "tax_percent": 0}],
    }
    cn_file = tmp_path / "cn.xml"
    cn_file.write_bytes(generate_credit_note(cn_data))

    captured: dict = {}

    def fake_package(xml_bytes: bytes, sender: str, recipient: str, process_type: str, document_type: str) -> dict:
        captured["document_type"] = document_type
        captured["process_type"] = process_type
        return {"packaged": True}

    def fake_send(message_body: dict, api_key: str, base_url: str) -> dict:
        captured["sent"] = True
        return {"status_code": 200, "json": {"messageId": "abc"}}

    monkeypatch.setenv("PEPPYRUS_API_KEY", "test-key")
    monkeypatch.setenv("PEPPOL_SENDER_ID", "9925:test")
    monkeypatch.setattr(cli, "package_message", fake_package)
    monkeypatch.setattr(cli, "send_message", fake_send)

    args = MagicMock()
    args.file = str(cn_file)
    args.recipient = "9908:test"
    args.processType = None
    args.documentType = None
    cli.cmd_send(args)

    assert captured["sent"] is True
    assert captured["document_type"] == CREDIT_NOTE_DOCUMENT_TYPE


def test_cmd_send_auto_detects_invoice_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import cli
    from peppol_sender.api import INVOICE_DOCUMENT_TYPE
    from peppol_sender.ubl import generate_ubl

    inv_data = {
        "invoice_number": "INV-X",
        "issue_date": "2025-02-01",
        "due_date": "2025-03-01",
        "currency": "EUR",
        "seller": {
            "name": "S",
            "registration_name": "S BV",
            "endpoint_id": "BE0123456789",
            "endpoint_scheme": "0208",
            "country": "BE",
        },
        "buyer": {
            "name": "B",
            "registration_name": "B BV",
            "endpoint_id": "NL987654321",
            "endpoint_scheme": "0208",
            "country": "NL",
        },
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.0, "tax_category": "E", "tax_percent": 0}],
    }
    inv_file = tmp_path / "inv.xml"
    inv_file.write_bytes(generate_ubl(inv_data))

    captured: dict = {}

    def fake_package(xml_bytes: bytes, sender: str, recipient: str, process_type: str, document_type: str) -> dict:
        captured["document_type"] = document_type
        return {}

    monkeypatch.setenv("PEPPYRUS_API_KEY", "test-key")
    monkeypatch.setenv("PEPPOL_SENDER_ID", "9925:test")
    monkeypatch.setattr(cli, "package_message", fake_package)
    monkeypatch.setattr(cli, "send_message", lambda *a, **kw: {"status_code": 200, "json": {}})

    args = MagicMock()
    args.file = str(inv_file)
    args.recipient = "9908:test"
    args.processType = None
    args.documentType = None
    cli.cmd_send(args)

    assert captured["document_type"] == INVOICE_DOCUMENT_TYPE


def test_cmd_send_document_type_override_honored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The --documentType escape hatch should win over auto-detection.
    import cli
    from peppol_sender.ubl import generate_ubl

    inv_data = {
        "invoice_number": "INV-X",
        "issue_date": "2025-02-01",
        "currency": "EUR",
        "seller": {
            "name": "S",
            "registration_name": "S BV",
            "endpoint_id": "BE0123456789",
            "endpoint_scheme": "0208",
            "country": "BE",
        },
        "buyer": {
            "name": "B",
            "registration_name": "B BV",
            "endpoint_id": "NL987654321",
            "endpoint_scheme": "0208",
            "country": "NL",
        },
        "lines": [{"id": "1", "quantity": 1, "unit_price": 100.0, "tax_category": "E", "tax_percent": 0}],
    }
    inv_file = tmp_path / "inv.xml"
    inv_file.write_bytes(generate_ubl(inv_data))

    captured: dict = {}
    monkeypatch.setenv("PEPPYRUS_API_KEY", "test-key")
    monkeypatch.setenv("PEPPOL_SENDER_ID", "9925:test")

    def fake_package(xml_bytes: bytes, sender: str, recipient: str, process_type: str, document_type: str) -> dict:
        captured["document_type"] = document_type
        return {}

    monkeypatch.setattr(cli, "package_message", fake_package)
    monkeypatch.setattr(cli, "send_message", lambda *a, **kw: {"status_code": 200, "json": {}})

    args = MagicMock()
    args.file = str(inv_file)
    args.recipient = "9908:test"
    args.processType = None
    args.documentType = "custom::doc::type"
    cli.cmd_send(args)

    assert captured["document_type"] == "custom::doc::type"
