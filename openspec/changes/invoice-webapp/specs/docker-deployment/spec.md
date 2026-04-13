# Docker Deployment

## ADDED Requirements

### Requirement: Container image

The project MUST provide a Dockerfile that builds a single image containing the `peppol_sender` package, CLI, and webapp.

#### Scenario: Build image

- **WHEN** `docker build -t peppol-sender .` is run
- **THEN** a working image is produced with all runtime dependencies installed

### Requirement: Docker Compose services

The project MUST provide a `docker-compose.yml` defining the webapp service.

#### Scenario: Start webapp

- **WHEN** `docker compose up webapp` is run
- **THEN** the Flask webapp is accessible on the configured port

#### Scenario: Environment configuration

- **WHEN** the container starts
- **THEN** it reads `PEPPYRUS_API_KEY`, `PEPPOL_SENDER_ID`, and `PEPPYRUS_BASE_URL` from environment variables or `.env` file
