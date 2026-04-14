# Invoice JSON schema

Reference for the JSON input accepted by `cli.py create` and the webapp's
`/api/validate` and `/api/send` routes.

See [`sample_invoice.json`](../sample_invoice.json) for a complete, working example.

## Example

```json
{
  "invoice_number": "INV-2025-001",
  "issue_date": "2025-11-29",
  "due_date": "2025-12-20",
  "invoice_type_code": "380",
  "currency": "EUR",
  "payment_terms": "Net 21 days",
  "seller": {
    "name": "ACME Consulting",
    "registration_name": "ACME Consulting BV",
    "endpoint_id": "0123456789",
    "endpoint_scheme": "0208",
    "vat": "BE0123456789",
    "legal_id": "0123456789",
    "legal_id_scheme": "0208",
    "country": "BE",
    "street": "Main Street 1",
    "city": "Brussels",
    "postal_code": "1000",
    "contact_name": "Jane Doe",
    "contact_email": "jane@example.be",
    "contact_phone": "+32 14 00 00 00"
  },
  "buyer": {
    "name": "Client Corp",
    "registration_name": "Client Corp BV",
    "endpoint_id": "987654321",
    "endpoint_scheme": "0208",
    "vat": "NL987654321B01",
    "legal_id": "987654321",
    "country": "NL",
    "street": "Client Ave 42",
    "city": "Amsterdam",
    "postal_code": "1011"
  },
  "lines": [
    {
      "id": "1",
      "description": "Consulting service",
      "quantity": 1,
      "unit": "HUR",
      "unit_price": 1000.00,
      "tax_category": "E",
      "tax_percent": 0,
      "service_date": "2025-11-20"
    }
  ]
}
```

## Top-level fields

| Field | Type | Description |
|---|---|---|
| `invoice_number` | string | Invoice identifier |
| `issue_date` | string | ISO 8601 date (YYYY-MM-DD); defaults to today |
| `due_date` | string | Payment due date (optional) |
| `invoice_type_code` | string | UBL type code (default: `380` = commercial invoice) |
| `currency` | string | ISO 4217 currency code (e.g. `EUR`) |
| `payment_terms` | string | Free-text payment terms; multi-line supported |

## Party fields (`seller` and `buyer`)

| Field | Type | UBL / EN-16931 | Description |
|---|---|---|---|
| `name` | string | BT-28 / BT-45 | Trading name |
| `registration_name` | string | BT-27 / BT-44 | Legal registration name (defaults to `name`) |
| `endpoint_id` | string | BT-34 / BT-49 | Electronic address (e.g. enterprise number, no country prefix) |
| `endpoint_scheme` | string | `@schemeID` | Endpoint scheme ID (default: `0208` for Belgian CBE) |
| `vat` | string | BT-31 / BT-48 | VAT identifier (e.g. `BE0674415660`) |
| `legal_id` | string | BT-30 / BT-47 | Legal registration identifier (usually the enterprise number) |
| `legal_id_scheme` | string | `@schemeID` | Optional scheme ID for `legal_id` (e.g. `0208` for Belgium) |
| `country` | string | BT-40 / BT-55 | ISO 3166-1 alpha-2 country code (uppercase) |
| `street` | string | BT-35 / BT-50 | Street address (optional) |
| `city` | string | BT-37 / BT-52 | City (optional) |
| `postal_code` | string | BT-38 / BT-53 | Postal code (optional) |
| `contact_name` | string | BT-41 / BT-56 | Contact person name (optional) |
| `contact_email` | string | BT-43 / BT-58 | Contact email (optional) |
| `contact_phone` | string | BT-42 / BT-57 | Contact phone (optional) |

## Line item fields (`lines[]`)

| Field | Type | Description |
|---|---|---|
| `id` | string | Line item identifier |
| `description` | string | Item description |
| `quantity` | number | Quantity |
| `unit` | string | UN/CEFACT Rec. 20 unit code (default: `EA`) — e.g. `HUR`, `DAY`, `KGM`, `LTR` |
| `unit_price` | number | Price per unit |
| `line_extension_amount` | number | Optional; defaults to `quantity * unit_price` |
| `tax_category` | string | VAT category: `S`, `E`, `O`, `Z`, `AE`, `K`, `G`, `L`, `M` |
| `tax_percent` | number | VAT rate (use `0` for exempt categories) |
| `service_date` | string | Optional service date (BT-134/135) — emitted as a single-day `InvoicePeriod` |
| `service_start_date` | string | Optional period start date (alternative to `service_date`) |
| `service_end_date` | string | Optional period end date |

## VAT category codes

| Code | Meaning |
|---|---|
| `S` | Standard rate |
| `E` | Exempt from VAT |
| `O` | Not subject to VAT |
| `Z` | Zero rated |
| `AE` | Reverse charge |
| `K` | Intra-EU supply |
| `G` | Export |
| `L` | Canary Islands (IGIC) |
| `M` | Ceuta / Melilla (IPSI) |

For VAT-exempt small businesses, use `E` (or `O`) with `tax_percent: 0`. The
generator automatically adds a `TaxExemptionReason` element when either of
these categories is used.

## Notes

- All optional fields can be omitted entirely — they are simply not emitted in the XML.
- ISO country codes (`country`, `seller.country`, `buyer.country`) must be uppercase to satisfy PEPPOL rule `BR-CL-14`.
- Unit codes must be valid UN/CEFACT Rec. 20 codes to satisfy `BR-CL-23`. The webapp uses a strict dropdown of 16 common codes; the CLI accepts any string but only valid codes will pass Peppyrus's server-side validation.
