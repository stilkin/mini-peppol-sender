# Webapp API

## ADDED Requirements

### Requirement: PDF preview endpoint

The Flask backend MUST expose a route that renders the current invoice JSON as a PDF and returns the bytes. This route is used by the webapp's `Preview PDF` button and is separate from the validate / send routes.

#### Scenario: POST /api/preview-pdf returns a PDF

- **WHEN** the frontend POSTs invoice JSON to `/api/preview-pdf`
- **THEN** the backend calls `render_pdf()` and returns the resulting bytes with `Content-Type: application/pdf` and an appropriate `Content-Disposition` header

#### Scenario: Preview endpoint does not transmit via Peppyrus

- **WHEN** `/api/preview-pdf` is called
- **THEN** no Peppyrus API call is made — only `render_pdf()` is invoked

#### Scenario: Preview error handling

- **WHEN** `render_pdf()` raises an exception (e.g. missing WeasyPrint system libraries or a template error)
- **THEN** the route returns an HTTP 500 with a JSON body containing an `error` field whose message is actionable (names the missing library or the template error), not a raw stack trace
