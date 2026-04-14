# Webapp UI

## ADDED Requirements

### Requirement: Preview PDF button

The webapp MUST provide a `Preview PDF` button on the invoice form that renders the current form state as a PDF and opens it for viewing. This lets the user see the human-readable representation that receivers will see, before committing to Send.

#### Scenario: Preview PDF from current form state

- **WHEN** the user clicks `Preview PDF` on the invoice form
- **THEN** the current form data is POSTed to `/api/preview-pdf` and the returned PDF is opened in a new browser tab (or an embedded viewer)

#### Scenario: Preview does not transmit the invoice

- **WHEN** the user clicks `Preview PDF`
- **THEN** no Peppyrus API call is made — only the local PDF rendering route is invoked

#### Scenario: Preview surfaces render errors

- **WHEN** the backend `render_pdf()` call fails (e.g. missing system libraries)
- **THEN** the button handler displays the error message inline in the form's status area rather than opening an empty tab
