# Webapp API

## ADDED Requirements

### Requirement: Serve invoice form

The Flask backend MUST serve the single-page invoice form.

#### Scenario: GET /

- **WHEN** a browser requests `GET /`
- **THEN** the invoice form HTML page is returned

### Requirement: Proxy organization info

The Flask backend MUST proxy Peppyrus organization API calls to keep the API key server-side.

#### Scenario: GET /api/org-info

- **WHEN** the frontend requests `/api/org-info`
- **THEN** the backend calls Peppyrus `/organization/info` with the server-side API key and returns the organization details as JSON

### Requirement: Proxy participant lookup

The Flask backend MUST proxy PEPPOL participant lookups.

#### Scenario: GET /api/lookup with VAT number

- **WHEN** the frontend requests `/api/lookup?vatNumber=...&countryCode=...`
- **THEN** the backend calls Peppyrus `/peppol/bestMatch` and returns the participant details as JSON

#### Scenario: GET /api/search by name

- **WHEN** the frontend requests `/api/search?name=...&country=...`
- **THEN** the backend calls Peppyrus `/peppol/search` and returns matching business cards as JSON

### Requirement: Validate and send invoice

The Flask backend MUST accept invoice data, generate UBL XML, validate, and optionally send.

#### Scenario: POST /api/validate

- **WHEN** the frontend POSTs invoice JSON to `/api/validate`
- **THEN** the backend generates UBL XML, runs basic + XSD validation, and returns the list of rules as JSON

#### Scenario: POST /api/send

- **WHEN** the frontend POSTs invoice JSON to `/api/send`
- **THEN** the backend generates UBL XML, validates it, and if no FATAL rules exist, sends it via Peppyrus and returns the response
