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

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _dec(value: object) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _build_view_model(invoice: dict[str, Any]) -> dict[str, Any]:
    """Pre-compute all display values so the template stays logic-free.

    Totals use the same (tax_category, tax_percent) grouping and Decimal
    rounding as ubl.py:_add_tax_total, so the PDF's grand total equals the
    XML's LegalMonetaryTotal/PayableAmount byte-for-byte.
    """
    currency = invoice.get("currency", "EUR")
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
        line_sum += ext
        groups[(cat, pct)] += ext
        display_lines.append(
            {
                "description": line.get("description", ""),
                "quantity": f"{qty:g}",
                "unit": line.get("unit", "EA"),
                "unit_price": f"{price:.2f}",
                "line_total": f"{ext:.2f}",
                "service_date": line.get("service_date"),
            }
        )

    tax_total = Decimal("0")
    for (_cat, pct), taxable in groups.items():
        tax_total += _dec(taxable * pct / 100)

    return {
        "invoice": invoice,
        "seller": invoice.get("seller", {}),
        "buyer": invoice.get("buyer", {}),
        "payment_means": invoice.get("payment_means"),
        "lines": display_lines,
        "currency": currency,
        "subtotal": f"{line_sum:.2f}",
        "tax_total": f"{tax_total:.2f}",
        "grand_total": f"{line_sum + tax_total:.2f}",
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
