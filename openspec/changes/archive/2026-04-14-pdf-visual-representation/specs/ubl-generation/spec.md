# UBL Generation

## MODIFIED Requirements

### Requirement: Generate UBL invoice from JSON

The generator MUST produce a fully EN-16931 compliant UBL 2.1 Invoice XML from a JSON invoice data structure, including all mandatory fields required by PEPPOL BIS Billing 3.0. When embedding is enabled (the default), the generator MUST also embed a single `cac:AdditionalDocumentReference` containing a rendered PDF of the invoice, positioned between `BuyerReference` and the party references per the UBL `xs:sequence`.

#### Scenario: Embed visual representation (PDF) — default

- **WHEN** `generate_ubl()` is called with its default `embed_pdf=True` argument
- **THEN** the generated XML contains exactly one `cac:AdditionalDocumentReference` positioned after `cbc:BuyerReference` and before `cac:AccountingSupplierParty`, containing `cbc:ID` (the invoice number), `cbc:DocumentDescription` (e.g. `"Commercial Invoice"`), and `cac:Attachment/cbc:EmbeddedDocumentBinaryObject` with `mimeCode="application/pdf"`, `filename="<invoice_number>.pdf"`, and base64-encoded PDF bytes as element text

#### Scenario: PDF content matches invoice data

- **WHEN** an invoice is rendered and embedded
- **THEN** the base64-decoded PDF bytes start with `%PDF-` and can be parsed by a PDF library, and the extracted text contains the invoice number, seller name, and payable total

#### Scenario: Single visual representation per invoice

- **WHEN** an invoice is generated with PDF embedding enabled
- **THEN** exactly one `cac:AdditionalDocumentReference` with an embedded PDF is emitted (matching PEPPOL-EN16931-R008)

#### Scenario: PDF embedding opt-out

- **WHEN** `generate_ubl()` is called with `embed_pdf=False`
- **THEN** no `cac:AdditionalDocumentReference` element is emitted and the rest of the XML is unchanged
