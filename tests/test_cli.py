"""Smoke tests for cli.py — run subcommands as subprocesses."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI = PROJECT_ROOT / "cli.py"
SAMPLE_JSON = PROJECT_ROOT / "sample_invoice.json"


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
