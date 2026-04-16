# Docker smoke test for Peppify

Short runbook for verifying the production Docker build on a host that actually has Docker. Maintained for one purpose: closing out the deferred checklist items in `openspec/changes/production-deployment/tasks.md` (sections 3.2, 4.x, 5.4, 5.5, 7.2).

The Python/gunicorn run path is already verified on the primary dev machine. This document covers **only the Docker path**, which that machine couldn't test because it has no Docker daemon.

## Who this is for

Anyone with a working Docker / Docker Desktop install. Tested target: Apple Silicon (M1 Pro, macOS) with Docker Desktop — the image base is `python:3.12-slim-bookworm`, which has a native `linux/arm64` build, so no emulation is needed.

## What you need

- A clone of this repo on a branch that contains `Dockerfile`, `.dockerignore`, and `docker-compose.yml` at the repo root
- Docker (engine + CLI) or Docker Desktop, running
- A `.env` file at the repo root with at least:
  ```
  PEPPYRUS_API_KEY=dummy
  PEPPOL_SENDER_ID=0208:be0000000000
  PEPPYRUS_BASE_URL=https://api.test.peppyrus.be/v1
  ```
  Dummy values are fine. The smoke test does not call the real Peppyrus API — it only verifies that the container starts, serves HTTP, and can render a PDF. You can copy `.env.example` and edit.
- About 10 minutes. First `docker build` is slow (apt + dependency resolution); subsequent builds are cached.

## Running the tests

Run each step in order from the repo root. Stop at the first failure and report it — don't guess around a broken step.

### 1. Build context sanity check (task 3.2)

```bash
docker build --progress=plain -t peppify:dev . 2>&1 | head -20
```

**Expect**: near the top of the output, a line like `transferring context: <N>kB`. That number should be **well under 10 MB** (realistically a few hundred kB to low single-digit MB). If it's 50+ MB, the `.dockerignore` isn't doing its job — report it and stop.

### 2. Full image build (task 4.1)

```bash
docker build -t peppify:dev .
docker images peppify:dev
```

**Expect**:
- Build succeeds with exit code 0
- A final image tagged `peppify:dev`
- Image size roughly **400–550 MB**. Record the actual number — we want it for the PR description (task 4.7).

If `apt-get install` fails on a missing package name, WeasyPrint's upstream Debian install docs (https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-ubuntu) have the authoritative list. Report which package was missing and what the error said.

### 3. Run the container (tasks 4.2, 4.3, 4.6)

```bash
docker run --rm -d --name peppify-smoke \
  -p 127.0.0.1:5000:5000 \
  --env-file .env \
  peppify:dev

sleep 2
curl -sS -o /tmp/peppify-index.html -w "HTTP=%{http_code} SIZE=%{size_download}\n" http://127.0.0.1:5000/
```

**Expect**:
- `HTTP=200` and a non-trivial `SIZE` (≳10 kB) — that's the index page
- Then:
  ```bash
  docker logs peppify-smoke 2>&1 | grep -c "development server"
  ```
  Should print `0`. Any non-zero means gunicorn didn't start and Flask's dev server is running inside the container — report it.

### 4. Flask routing reach check (task 4.4)

```bash
curl -sS -w "HTTP=%{http_code}\n" http://127.0.0.1:5000/api/org-info
```

**Expect**: `HTTP=200`, `HTTP=401`, `HTTP=500`, or similar — anything **except** `HTTP=000` (connection refused) or `HTTP=404`. We're not testing Peppyrus API correctness here, only that Flask routes the request. A 500 from the route handler is fine: it proves the route exists and executed.

### 5. PDF rendering (task 4.5) — **the critical test**

This is the one that proves WeasyPrint's native deps (Pango, Cairo, GDK-PixBuf, fontconfig, fonts) are all present inside the image. If the container can render a PDF, the whole PDF pipeline works in production.

```bash
curl -sS -X POST http://127.0.0.1:5000/api/preview-pdf \
  -H 'Content-Type: application/json' \
  -d @sample_invoice.json \
  -o /tmp/peppify-preview.pdf \
  -w "HTTP=%{http_code} SIZE=%{size_download} TYPE=%{content_type}\n"

file /tmp/peppify-preview.pdf
```

**Expect**:
- `HTTP=200`
- `TYPE=application/pdf`
- `SIZE` around 25–40 kB (the reference render on the dev machine was 28 kB)
- `file` output starts with `PDF document, version 1.7`
- Opening the file in a viewer shows the invoice with proper typography (not blank, not garbled)

If you get an HTTP 500, `docker logs peppify-smoke` will tell you which native library is missing. Report the traceback.

### 6. Stop the container

```bash
docker stop peppify-smoke
```

### 7. docker-compose lifecycle (task 5.4)

```bash
docker compose up --build -d
sleep 2
curl -sS -w "HTTP=%{http_code}\n" http://127.0.0.1:5000/
docker compose down
docker volume ls | grep peppify || echo "no peppify volumes (good)"
docker network ls | grep peppol || echo "no peppify networks (good)"
```

**Expect**:
- `docker compose up --build -d` brings the service up cleanly
- `curl` returns `HTTP=200`
- `docker compose down` removes the container
- No leftover volumes or named networks after `down`

### 8. LAN negative test (task 5.5) — **security-critical**

This verifies that the compose loopback binding (`127.0.0.1:5000:5000`) actually prevents LAN access. The whole no-auth security story depends on it.

Start the service again:

```bash
docker compose up -d
```

Find the host's LAN IP:

```bash
# macOS
ipconfig getifaddr en0
# Linux
hostname -I | awk '{print $1}'
```

From **another machine on the same LAN** (a phone on WiFi works — `http://<ip>:5000/` in the browser) try to reach `http://<LAN-IP>:5000/`. You can also test from the host itself using its LAN IP (that's a weaker test but catches obvious bind-address mistakes):

```bash
curl --max-time 3 -sS -w "HTTP=%{http_code}\n" http://<LAN-IP>:5000/ || echo "unreachable (good)"
```

**Expect**: connection refused / timeout / "unreachable". If you can actually load the page from another device, the binding is wrong and the issue should be reported immediately before anything ships — this is the whole point of the loopback restriction.

Tear it down:

```bash
docker compose down
```

### 9. Fresh-clone sanity (task 7.2)

To rule out any host-machine contamination, clone the branch fresh into a tmp dir and repeat steps 2–5:

```bash
git clone --branch development https://github.com/stilkin/peppify.git /tmp/peppify-fresh
cd /tmp/peppify-fresh
cp /path/to/your/.env .env
docker build -t peppify:fresh .
docker run --rm -d --name peppify-fresh -p 127.0.0.1:5001:5000 --env-file .env peppify:fresh
sleep 2
curl -sS http://127.0.0.1:5001/ -o /dev/null -w "HTTP=%{http_code}\n"
curl -sS -X POST http://127.0.0.1:5001/api/preview-pdf \
  -H 'Content-Type: application/json' -d @sample_invoice.json \
  -o /tmp/peppify-fresh.pdf -w "HTTP=%{http_code} TYPE=%{content_type}\n"
file /tmp/peppify-fresh.pdf
docker stop peppify-fresh
```

Same expectations as steps 2 and 5.

## What to report back

A short message with:

1. **Host info**: `docker version` short output, OS + arch (e.g. `macOS 14, arm64`)
2. **For each step 1–9**: pass/fail and the one line of output that proves it (the `HTTP=...` / `SIZE=...` / `file` / `docker images` line)
3. **Image size** from step 2 (`docker images peppify:dev` → `SIZE` column)
4. **Any deviations**: missing apt packages, unexpected errors, anything that required guessing

If every step passes, that's enough to tick off tasks 3.2, 4.1–4.7, 5.4, 5.5, and 7.2 in `openspec/changes/production-deployment/tasks.md`.

## Troubleshooting — common gotchas

- **Build fails at `apt-get install` with "package not found"**: WeasyPrint's Debian package names drifted. Compare the `RUN apt-get install` line in the `Dockerfile` against WeasyPrint's current upstream install docs and report the diff.
- **`HTTP=000` on curl**: the container is not reachable. Run `docker ps` to confirm it's up, `docker logs peppify-smoke` to see why it isn't.
- **PDF endpoint returns 500 with `OSError: cannot load library`**: a native library is missing from the image. The traceback in `docker logs` names it. That's the signal to expand the `RUN apt-get install` list in the `Dockerfile`.
- **Port 5000 already in use on the host** (macOS has AirPlay Receiver on 5000 by default): remap both the `docker run` flag and the `docker-compose.yml` mapping to `127.0.0.1:5050:5000` and adjust the curl URLs.
- **Docker Desktop on M1 shows a warning about platform mismatch**: ignore — `python:3.12-slim-bookworm` has a native `linux/arm64` manifest and will be pulled automatically.
