# VPS Deployment (Docker + Caddy + sslip.io + Cloudflare Pages) Plan

> **For agentic workers:** This is a **manual operator runbook**, not an agent-executed plan. It touches a live VPS, public DNS, a firewall, and a Cloudflare account — perform these steps yourself (you = the operator on the VPS / at the Cloudflare dashboard). Do NOT hand this to a subagent. Steps use checkbox (`- [ ]`) syntax so you can track progress.

**Goal:** Run the fiscoscope FastAPI app as an always-on, HTTPS, rate-limited, firewalled service on the VPS (TLS via an `<ip>.sslip.io` Let's Encrypt cert), keep its data fresh via a scheduled containerized pipeline run, and stand up a Cloudflare Pages project so the frontend origin + CORS are ready.

**Architecture:** A Docker Compose stack on the VPS with three services off one image: `api` (uvicorn serving `backend/data/output/*.json`, internal-only — never published to the host), `caddy` (reverse proxy owning host ports 80/443, auto-provisioning + renewing the Let's Encrypt cert for the sslip.io hostname, proxying to `api`), and `pipeline` (one-shot, `profiles: [tools]`, invoked by host cron to refresh the data). The API is reachable from the internet *only* through Caddy; abuse is bounded by in-app slowapi rate limiting + a host firewall. The frontend lives on Cloudflare Pages and calls the API cross-origin (allowed via the CORS allowlist).

**Tech stack:** Docker + Docker Compose v2, Caddy 2, uvicorn/FastAPI (already built), sslip.io (free wildcard DNS), Let's Encrypt, ufw, cron, Cloudflare Pages (free).

**Confirmed environment (checked 2026-05-22):** repo at `/home/arnobgr/french-efficiency-dashboard`, user `arnobgr`, Docker at `/usr/bin/docker`, `docker compose` works without sudo (you're in the docker group). The VPS already runs *other* FastAPI services on host port **8000** (`uvicorn app.main:app` as root, `uvicorn main:app` as botuser) — these are NOT part of this project; this stack must not disturb them, and the API container is deliberately **not** published to the host so it won't collide with anything.

---

## File map (all created at the repo root on the VPS)

| File | Responsibility |
|------|----------------|
| `Dockerfile` | Build one image containing the backend (used by both `api` and `pipeline`) |
| `.dockerignore` | Keep `.venv`, `data`, `.git`, frontend, docs out of the build context |
| `docker-compose.yml` | Define `api`, `caddy`, `pipeline` services + cert volumes |
| `Caddyfile` | One site block: terminate TLS for the sslip.io host, reverse-proxy to `api:8000` |
| `.env` | Operator-supplied, gitignored: `SITE_ADDRESS`, `ALLOWED_ORIGINS`, `RATE_LIMIT` |

These are deployment artifacts; committing them to the repo is recommended (Phase 1, last step) but optional.

---

## Phase 0: Preflight — gather facts and verify the host

- [ ] **Step 0.1: Confirm Docker + Compose are usable (no sudo)**

```bash
docker --version
docker compose version
docker ps
```
Expected: versions print and `docker ps` lists running containers with **no permission error**. (If you get a permission error, run `sudo usermod -aG docker $USER`, then log out and back in.)

- [ ] **Step 0.2: Find the VPS public IP and derive the sslip.io hostname**

```bash
curl -s https://api.ipify.org; echo
```
Example output: `203.0.113.45`. Your sslip.io hostname is that IP **with dashes**: `203-0-113-45.sslip.io`. Write it down — you'll use it as `SITE_ADDRESS`. (Dashed form avoids any dotted-label edge cases.)

- [ ] **Step 0.3: Confirm the sslip.io hostname resolves to your IP**

```bash
getent hosts 203-0-113-45.sslip.io
```
Replace with your hostname. Expected: a line showing **your** public IP. (sslip.io resolves the embedded IP automatically — if this is empty, re-check the dashes.)

- [ ] **Step 0.4: Confirm host ports 80 and 443 are free** (Caddy needs them; Let's Encrypt validates over them)

```bash
sudo ss -ltnp '( sport = :80 or sport = :443 )'
```
Expected: **no output** (nothing listening). If something is already on 80/443 (e.g. a pre-existing nginx for your other projects), STOP — you have a host reverse proxy already; see "Alternative: existing host proxy" at the bottom before continuing, because two things can't both own 443.

- [ ] **Step 0.5: Decide your Cloudflare Pages project name now** so CORS can be wired later. Pick e.g. `fiscoscope` → the URL will be `https://fiscoscope.pages.dev` (if the name is taken globally, Cloudflare appends a random suffix; you'll capture the real URL in Phase 5). Note your choice.

---

## Phase 1: Create the deployment files

All files are created at the repo root: `/home/arnobgr/french-efficiency-dashboard`.

- [ ] **Step 1.1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install runtime deps first for layer caching.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend source (api.py, run_pipeline.py, config.py, fetchers/, processors/).
COPY backend/ .

EXPOSE 8000

# Default command = the API. The pipeline service overrides the entrypoint.
# --proxy-headers + --forwarded-allow-ips=* let uvicorn trust Caddy's
# X-Forwarded-For so slowapi rate-limits on the real client IP (safe here:
# only Caddy can reach this container).
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=*"]
```

- [ ] **Step 1.2: Create `.dockerignore`**

```
backend/.venv
backend/data
**/__pycache__
*.pyc
.git
frontend
docs
```

- [ ] **Step 1.3: Create `docker-compose.yml`**

```yaml
services:
  api:
    build: .
    image: fiscoscope-backend
    restart: unless-stopped
    environment:
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
      RATE_LIMIT: ${RATE_LIMIT:-60/minute}
    volumes:
      # Bind the host data dir so the API serves whatever the pipeline writes.
      - ./backend/data:/app/data
    expose:
      - "8000"          # internal to the compose network only — NOT published to the host

  caddy:
    image: caddy:2
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      SITE_ADDRESS: ${SITE_ADDRESS}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data       # persists issued certs across restarts (avoids re-issuing)
      - caddy_config:/config
    depends_on:
      - api

  pipeline:
    build: .
    image: fiscoscope-backend
    profiles: ["tools"]        # never starts with `up`; run on demand / via cron
    volumes:
      - ./backend/data:/app/data
    entrypoint: ["python", "run_pipeline.py"]

volumes:
  caddy_data:
  caddy_config:
```

- [ ] **Step 1.4: Create `Caddyfile`**

```
{$SITE_ADDRESS} {
	reverse_proxy api:8000
}
```

(Caddy reads `$SITE_ADDRESS` from the container env; it redirects HTTP→HTTPS and runs the ACME challenge automatically.)

- [ ] **Step 1.5: Create `.env`** (this file is already covered by `.gitignore` — do NOT commit it). Substitute your real hostname and Pages URL from Phase 0:

```
SITE_ADDRESS=203-0-113-45.sslip.io
ALLOWED_ORIGINS=https://fiscoscope.pages.dev
RATE_LIMIT=60/minute
```

- [ ] **Step 1.6: Verify `.env` is ignored** (so no secrets/host details get committed)

```bash
cd /home/arnobgr/french-efficiency-dashboard
git check-ignore .env && echo "OK: .env is gitignored"
```
Expected: `.env` then `OK: .env is gitignored`.

- [ ] **Step 1.7 (optional but recommended): Commit the deployment files**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git add Dockerfile .dockerignore docker-compose.yml Caddyfile
git commit -m "deploy: add Docker + Caddy stack for VPS serving"
```

---

## Phase 2: Firewall (ufw)

> **Read this before running anything.** Two hazards: (1) enabling ufw with default-deny can lock you out of SSH — always allow SSH first; (2) your existing services on host port **8000** are plain host processes that ufw governs — if anything reaches them directly over the internet on `:8000`, denying it will cut them off. Decide before enabling. (Note: Docker-published ports like Caddy's 80/443 bypass ufw via Docker's own iptables rules — that's fine, we want them open. The `api` container is not published, so it is never exposed regardless.)

- [ ] **Step 2.1: Check current firewall state**

```bash
sudo ufw status verbose
```
- If it shows `Status: active` (you already firewalled this box for another project), skip to Step 2.2 to just add 80/443.
- If `Status: inactive` and you want to enable it, do Steps 2.2 + 2.3.
- If you manage the firewall another way (cloud provider security groups, nftables), skip ufw entirely and instead ensure **80 and 443 are open inbound** there, and continue to Phase 3.

- [ ] **Step 2.2: Allow the required ports** (run the SSH line FIRST)

```bash
sudo ufw allow OpenSSH                 # keep your SSH session alive
sudo ufw allow 80/tcp                  # ACME challenge + HTTP→HTTPS redirect
sudo ufw allow 443/tcp                 # the API over HTTPS
# ONLY if your other :8000 services must remain reachable from the internet:
# sudo ufw allow 8000/tcp
```

- [ ] **Step 2.3: Enable (only if it was inactive) and verify**

```bash
sudo ufw enable
sudo ufw status verbose
```
Expected: `Status: active`, with allow rules for 22/OpenSSH, 80, 443 (and 8000 only if you chose to). **Do not close this SSH session until you've confirmed you can open a second one.**

---

## Phase 3: Build and launch the API + Caddy stack

- [ ] **Step 3.1: Build the image and start `api` + `caddy`**

```bash
cd /home/arnobgr/french-efficiency-dashboard
docker compose up -d --build api caddy
```
Expected: image builds, two containers start. (`pipeline` is in the `tools` profile, so it correctly does NOT start here.)

- [ ] **Step 3.2: Confirm both containers are up**

```bash
docker compose ps
```
Expected: `api` and `caddy` both `running` (or `Up`). `api` shows no host port mapping; `caddy` shows `0.0.0.0:80->80, 0.0.0.0:443->443`.

- [ ] **Step 3.3: Watch Caddy obtain the certificate** (first issuance takes a few seconds)

```bash
docker compose logs caddy | grep -iE "certificate obtained|serving|tls"
```
Expected: a line indicating a certificate was obtained for your sslip.io host. If you see ACME errors, the usual cause is 80/443 not reachable from the internet (re-check Phase 2 / cloud security groups).

- [ ] **Step 3.4: Hit the API over HTTPS** (substitute your hostname)

```bash
curl -s --retry 10 --retry-delay 2 --retry-connrefused https://203-0-113-45.sslip.io/healthz; echo
```
Expected: `{"status":"ok"}` over a valid TLS connection (no `curl` cert warnings). At this point you have a public, trusted-HTTPS API.

---

## Phase 4: Populate data + schedule the pipeline

The `api` serves `backend/data/output/*.json`. If that directory is empty (fresh box) or you want a first refresh, run the pipeline container once, then schedule it.

- [ ] **Step 4.1: Run the pipeline once to produce/refresh the data**

```bash
cd /home/arnobgr/french-efficiency-dashboard
docker compose run --rm pipeline --mode full
```
Expected: log lines for each fetcher/processor; ends with `Pipeline complete`. Some sources may log `skipped`/`error` (fail-soft by design, e.g. the expired Urssaf TLS cert) — that's fine as long as it finishes. Files land in `./backend/data/output/` (written as root via the container — readable on the host; use `sudo` if you ever need to edit/delete them).

- [ ] **Step 4.2: Confirm the live API serves the fresh data**

```bash
curl -s https://203-0-113-45.sslip.io/api/kpis; echo
curl -s https://203-0-113-45.sslip.io/api/meta | head -c 120; echo
```
Expected: `{"kpis":[...]}` listing the KPI files, and a `meta` payload whose `last_run` is recent.

- [ ] **Step 4.3: Schedule periodic refreshes with cron**

```bash
crontab -e
```
Add these two lines (cron has a minimal PATH, so the absolute `docker` path and `cd` into the repo are required):

```cron
# fiscoscope: monthly sources — 5th of each month, 03:00
0 3 5 * * cd /home/arnobgr/french-efficiency-dashboard && /usr/bin/docker compose run --rm pipeline --mode monthly >> /home/arnobgr/fisc-pipeline.log 2>&1
# fiscoscope: annual sources — Feb 1 and Jun 1, 04:00 (per PRD: published May–June)
0 4 1 2,6 * cd /home/arnobgr/french-efficiency-dashboard && /usr/bin/docker compose run --rm pipeline --mode annual >> /home/arnobgr/fisc-pipeline.log 2>&1
```

- [ ] **Step 4.4: Verify the cron entries are registered**

```bash
crontab -l | grep fiscoscope
```
Expected: the two lines above. (The pipeline runs as your user via the docker group — no sudo needed.)

- [ ] **Step 4.5: Ensure Docker starts on boot** (so the stack comes back after a reboot; `restart: unless-stopped` then relaunches the containers)

```bash
sudo systemctl enable docker
```
Expected: `docker.service` enabled (or already enabled).

---

## Phase 5: Cloudflare Pages (reserve the frontend origin + wire CORS)

The frontend isn't built yet (Phase 2 of the project), but you can reserve the `*.pages.dev` subdomain now and point CORS at it so it's ready.

- [ ] **Step 5.1: Create a placeholder site to upload**

On your laptop (or the VPS), make a one-file placeholder:

```bash
mkdir -p /tmp/fisc-placeholder && printf '<!doctype html><title>fiscoscope</title><h1>fiscoscope — coming soon</h1>\n' > /tmp/fisc-placeholder/index.html
```

- [ ] **Step 5.2: Create the Pages project (dashboard route — easiest)**

1. Log in at `https://dash.cloudflare.com` (free account).
2. Left sidebar → **Workers & Pages** → **Create** → **Pages** tab → **Upload assets**.
3. Project name: the name you chose in Step 0.5 (e.g. `fiscoscope`).
4. Drag in the `index.html` from Step 5.1 (or the whole `/tmp/fisc-placeholder` folder) → **Deploy**.

(CLI alternative, if you prefer: `npx wrangler pages deploy /tmp/fisc-placeholder --project-name fiscoscope`.)

- [ ] **Step 5.3: Capture the real production URL**

After deploy, Cloudflare shows the URL, e.g. `https://fiscoscope.pages.dev` (it may differ if the name was taken). Confirm it loads:

```bash
curl -sI https://fiscoscope.pages.dev | head -1
```
Expected: `HTTP/2 200`. Note the exact URL.

- [ ] **Step 5.4: Point the API's CORS allowlist at that URL**

On the VPS, edit `.env` so `ALLOWED_ORIGINS` is the exact Pages URL (scheme + host, no trailing slash):

```
ALLOWED_ORIGINS=https://fiscoscope.pages.dev
```

Then recreate the `api` container so it picks up the new env (a plain `restart` does NOT reload env — use `up -d`):

```bash
cd /home/arnobgr/french-efficiency-dashboard
docker compose up -d api
```

- [ ] **Step 5.5: Verify the CORS header is returned for that origin**

```bash
curl -sI -H "Origin: https://fiscoscope.pages.dev" https://203-0-113-45.sslip.io/api/meta | grep -i access-control-allow-origin
```
Expected: `access-control-allow-origin: https://fiscoscope.pages.dev`. (A different/absent origin should NOT be echoed — that's the allowlist working.)

---

## Phase 6: Final verification + ongoing operations

- [ ] **Step 6.1: End-to-end check from a second SSH session and an external curl**

```bash
curl -s https://203-0-113-45.sslip.io/healthz; echo
curl -s https://203-0-113-45.sslip.io/api/kpis; echo
curl -s -o /dev/null -w "missing -> %{http_code}\n" https://203-0-113-45.sslip.io/api/kpi/nope
```
Expected: `{"status":"ok"}`, the KPI list, and `missing -> 404`.

- [ ] **Step 6.2: Confirm the stack survives a restart**

```bash
docker compose restart
docker compose ps
curl -s --retry 10 --retry-delay 2 https://203-0-113-45.sslip.io/healthz; echo
```
Expected: containers come back `running`; healthz returns ok (Caddy reuses the cert from the `caddy_data` volume — no re-issue).

### Operations cheat-sheet (keep for later)

- **Logs:** `docker compose logs -f api` and `docker compose logs -f caddy`.
- **Deploy code changes:** on the VPS, `cd` to the repo, `git pull` (the FastAPI code is on the `dev` branch — make sure you're on the branch you intend), then `docker compose up -d --build api`.
- **Manual data refresh:** `docker compose run --rm pipeline --mode full`.
- **Pipeline cron logs:** `tail -f /home/arnobgr/fisc-pipeline.log`.
- **Cert renewal:** automatic (Caddy renews well before expiry; certs persist in the `caddy_data` volume).
- **When the real frontend exists:** set its API base URL to `https://203-0-113-45.sslip.io/api`, and either re-deploy to the same Pages project (keeping the same origin so `ALLOWED_ORIGINS` still matches) or connect the Pages project to the Git repo (build output `frontend/dist`) for auto-deploys.

---

## Alternative: you already run a host reverse proxy on 443 (from Step 0.4)

If something already owns 443 on the host (e.g. an existing nginx for your other projects), do NOT add Caddy's 80/443 (they'd conflict). Instead:

1. In `docker-compose.yml`, drop the `caddy` service entirely, and on the `api` service replace `expose: ["8000"]` with a **localhost-only** publish so only the host proxy can reach it:
   ```yaml
       ports:
         - "127.0.0.1:8077:8000"
   ```
   (8077 chosen to avoid your in-use 8000.)
2. Add a vhost to your existing nginx for the sslip.io hostname, terminating TLS (certbot: `sudo certbot --nginx -d 203-0-113-45.sslip.io`) and proxying to `http://127.0.0.1:8077`, forwarding `X-Forwarded-For`/`X-Forwarded-Proto`.
3. Skip Phase 3's Caddy steps; verify via the same Phase 3.4 / Phase 6 curls. Everything else (firewall, pipeline cron, Cloudflare Pages, CORS) is unchanged.

---

## Self-review (plan vs. goal)

- **HTTPS on sslip.io:** Phase 0.2–0.3 (hostname), Phase 1.4 (`Caddyfile`), Phase 3 (Caddy issues cert) ✓
- **Always-on API, Docker-managed:** Phase 1.3 (`restart: unless-stopped`), Phase 3, Phase 4.5 (boot), Phase 6.2 ✓
- **Firewall:** Phase 2, with explicit SSH-lockout and existing-:8000 hazards, and the Docker/ufw bypass note ✓
- **Rate limiting:** in-app slowapi (already built) + `--proxy-headers`/`--forwarded-allow-ips` so it keys on the real client IP (Phase 1.1) ✓
- **Data freshness / scheduling (requested):** Phase 4 (manual run + monthly/annual cron + boot-persistence) ✓
- **Cloudflare Pages (requested):** Phase 5 (create project, capture URL, wire `ALLOWED_ORIGINS`, verify CORS) ✓
- **Doesn't disturb existing :8000 services:** API uses `expose` not `ports`; firewall step calls out 8000; alternative path for an existing host proxy ✓
- **No placeholders:** every step has exact commands/file contents; substitution points (your IP, your Pages URL) are explicitly flagged and shown with concrete examples ✓
