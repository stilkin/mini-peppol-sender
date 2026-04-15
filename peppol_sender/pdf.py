"""Render a human-readable invoice PDF from the same JSON used by ubl.py.

The output is embedded in outgoing UBL XML as cac:AdditionalDocumentReference
(the 'visual representation' permitted by PEPPOL BIS Billing 3.0 rule R008).

- `_build_view_model(invoice)` is a pure function — testable without WeasyPrint.
- `render_pdf(invoice)` is a thin wrapper that lazy-imports WeasyPrint so the
  system-lib tax (Pango / Cairo / libgdk-pixbuf) is only paid on actual render.
"""

from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

import jinja2

from peppol_sender import i18n
from peppol_sender.epc_qr import build_epc_payload, render_qr_svg

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _dec(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _build_view_model(invoice: dict[str, Any]) -> dict[str, Any]:
    """Pre-compute all display values so the template stays logic-free.

    Totals use the same (tax_category, tax_percent) grouping and Decimal
    rounding as ubl.py:_add_tax_total, so the PDF's grand total equals the
    XML's LegalMonetaryTotal/PayableAmount byte-for-byte (modulo the
    BeNeLux string format — cross-checks parse both sides back to Decimal).
    """
    currency = invoice.get("currency", "EUR")
    lang = (invoice.get("language") or "en").lower()
    labels = i18n.all_labels(lang)
    lines = invoice.get("lines", [])

    groups: dict[tuple[str, Decimal], Decimal] = defaultdict(lambda: Decimal("0"))
    line_sum = Decimal("0")
    display_lines: list[dict[str, Any]] = []

    for line in lines:
        qty = Decimal(str(line.get("quantity", 1)))
        price = Decimal(str(line.get("unit_price", 0)))
        ext = _dec(line.get("line_extension_amount", price * qty))
        cat = line.get("tax_category", "E")
        pct = Decimal(str(line.get("tax_percent", 0)))
        raw_unit = line.get("unit", "EA")
        line_sum += ext
        groups[(cat, pct)] += ext
        display_lines.append(
            {
                "description": line.get("description", ""),
                "quantity": f"{qty:g}",
                "unit": raw_unit,
                "unit_label": i18n.unit_label(lang, raw_unit),
                "unit_price": i18n.format_amount(_dec(price)),
                "line_total": i18n.format_amount(ext),
                "service_date": line.get("service_date"),
            }
        )

    tax_total = Decimal("0")
    for (_cat, pct), taxable in groups.items():
        tax_total += _dec(taxable * pct / 100)

    grand_total_dec = line_sum + tax_total

    epc_payload = build_epc_payload(invoice, grand_total_dec)
    epc_qr_svg = render_qr_svg(epc_payload) if epc_payload else None

    return {
        "invoice": invoice,
        "seller": invoice.get("seller", {}),
        "buyer": invoice.get("buyer", {}),
        "payment_means": invoice.get("payment_means"),
        "lines": display_lines,
        "currency": currency,
        "language": lang,
        "labels": labels,
        "subtotal": i18n.format_amount(line_sum),
        "tax_total": i18n.format_amount(tax_total),
        "grand_total": i18n.format_amount(grand_total_dec),
        "epc_qr_svg": epc_qr_svg,
    }


_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=jinja2.select_autoescape(["html"]),
)


def render_pdf(invoice: dict[str, Any]) -> bytes:
    """Render an invoice dict to PDF bytes using WeasyPrint.

    WeasyPrint is lazy-imported so importing peppol_sender.pdf does not require
    Pango/Cairo at the OS level unless the caller actually renders a PDF.
    """
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except ImportError as e:  # pragma: no cover - environment-specific
        raise RuntimeError(
            "WeasyPrint is required for PDF rendering but its system "
            "libraries (Pango, Cairo, libgdk-pixbuf) are not installed. "
            "See README install section for per-OS instructions."
        ) from e

    html = _env.get_template("invoice.html").render(**_build_view_model(invoice))
    pdf_bytes: bytes = HTML(string=html, base_url=str(_TEMPLATE_DIR)).write_pdf()
    return pdf_bytes
