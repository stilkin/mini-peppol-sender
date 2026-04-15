## 1. Gunicorn as an optional dependency

- [ ] 1.1 Add `[project.optional-dependencies].prod = ["gunicorn>=23.0"]` to `pyproject.toml`
- [ ] 1.2 Run `uv sync --extra prod` and verify `uv.lock` is updated and committed
- [ ] 1.3 Verify `uv run gunicorn webapp.app:app -b 127.0.0.1:5000 --workers 2` starts the app, answers `GET /`, and does NOT emit the Werkzeug "development server" warning
- [ ] 1.4 Verify that `uv sync` (without the `prod` extra) still works and `uv run pytest` passes without gunicorn installed

## 2. Dockerfile

- [ ] 2.1 Create `Dockerfile` based on `python:3.12-slim-bookworm`
- [ ] 2.2 Install WeasyPrint native deps via apt (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz0b`, `libcairo2`, `libgdk-pixbuf-2.0-0`, `libffi-dev`, `shared-mime-info`, `fonts-dejavu-core` — cross-check against WeasyPrint upstream install docs and trim/extend as needed)
- [ ] 2.3 Install `uv` in the image (pinned version, e.g. via the official `ghcr.io/astral-sh/uv` copy-from pattern or `pip install uv==<pin>`)
- [ ] 2.4 Set `WORKDIR /app`, copy `pyproject.toml` + `uv.lock` first, run `uv sync --frozen --no-dev --extra prod` as a cached layer
- [ ] 2.5 Copy application source (`webapp/`, `peppol_sender/`, `schemas/`, `cli.py`) in a later layer so source edits don't invalidate the dependency layer
- [ ] 2.6 `EXPOSE 5000` and set `CMD ["uv", "run", "gunicorn", "webapp.app:app", "-b", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]`
- [ ] 2.7 Create a non-root `appuser` in the image and `USER appuser` before `CMD`

## 3. Dockerignore

- [ ] 3.1 Create `.dockerignore` excluding `.venv/`, `.git/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.env`, `tests/`, `docs/`, `openspec/`, `.claude/`, `.opencode/`, `README.md` edit history, and any `*.xml` / `*.pdf` leftovers from local runs
- [ ] 3.2 Build the image and confirm the build context is small (< ~10 MB) via `docker build --progress=plain .` output

## 4. Build & smoke test

- [ ] 4.1 `docker build -t peppify:dev .` succeeds on a clean clone
- [ ] 4.2 `docker run --rm -p 127.0.0.1:5000:5000 --env-file .env peppify:dev` starts and serves the webapp
- [ ] 4.3 Hit `GET /` from the host and confirm the index page loads
- [ ] 4.4 Hit `GET /api/org-info` (with dummy env vars OK if the endpoint is gated) and confirm the route reaches Flask
- [ ] 4.5 Render a PDF inside the container via `POST /api/preview-pdf` with `sample_invoice.json` and confirm a valid PDF is returned (proves Pango/Cairo/fontconfig are present)
- [ ] 4.6 Confirm the Werkzeug dev-server warning is absent from `docker logs`
- [ ] 4.7 Record the resulting image size (`docker images peppify:dev`) in the PR description for future reference

## 5. docker-compose.yml

- [ ] 5.1 Create `docker-compose.yml` with one service `webapp` that builds from `.` and maps `"127.0.0.1:5000:5000"` (explicit loopback binding)
- [ ] 5.2 Add `env_file: .env` to the service
- [ ] 5.3 Add `restart: unless-stopped`
- [ ] 5.4 Verify `docker compose up --build` brings the app up and `docker compose down` tears it down cleanly, with no leftover volumes or named networks
- [ ] 5.5 Confirm from another machine on the LAN that port 5000 is NOT reachable (negative test for the loopback binding)

## 6. Documentation

- [ ] 6.1 Update `README.md` with three labeled sections: **Develop**, **Run with Python (production)**, **Run with Docker (production)**, each with a copy-pasteable command
- [ ] 6.2 Add a **Security** section to `README.md` stating: no built-in auth; default binding is `127.0.0.1`; any non-loopback exposure requires an authenticating reverse proxy
- [ ] 6.3 Update `CLAUDE.md` Commands section to include the gunicorn and Docker commands alongside the existing `uv run python webapp/app.py`
- [ ] 6.4 Add a one-line reference in `CLAUDE.md` pointing to the README Security section
- [ ] 6.5 Proofread both files and confirm the commands copy-paste cleanly

## 7. Verification & archive

- [ ] 7.1 Run the full local checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy .`, `uv run pytest`
- [ ] 7.2 Rebuild the Docker image from a fresh clone of the branch and re-run the smoke test in task 4 to confirm no host-machine contamination
- [ ] 7.3 Run `openspec validate production-deployment --strict` and resolve any findings
- [ ] 7.4 Open PR referencing this change directory; after merge, archive via `/openspec-archive-change`
