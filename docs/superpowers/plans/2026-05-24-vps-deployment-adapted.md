# VPS Deployment Plan — adapted to existing nginx + Tailscale + docker (2026-05-24)

> **Supersedes** `2026-05-22-vps-deployment.md` for your VPS. That original plan assumed an empty box with no reverse proxy. Your VPS already has:
> - System **nginx** on 80/443, certbot-managed, with two vhosts (artstamp on `159.69.91.118.sslip.io` → 127.0.0.1:8000, situation-room on `situation-room.159-69-91-118.sslip.io` → 127.0.0.1:8001).
> - Docker with three running projects (artstamp, situation-room, bot_wristshotai).
> - **Tailscale** up (`100.117.128.21`).
> - UFW active, allowing 80/443 from anywhere and SSH only from the tailnet.
> - certbot.timer running (auto-renewals).
>
> So: **no Caddy**, **no firewall changes**, **nginx becomes the reverse proxy** with a third vhost, and the api container binds to `127.0.0.1:8077` (since `0.0.0.0:8000` is already taken by artstamp).
>
> This is a manual operator runbook. Run each step yourself on the VPS.

**Goal:** Run the fiscoscope FastAPI app as an always-on, HTTPS, rate-limited service at `https://fisc.159-69-91-118.sslip.io`, fed by a scheduled containerized pipeline, with a Cloudflare Pages project reserved for the frontend.

**Architecture:** Docker Compose stack with two services off one image: `api` (uvicorn serving `backend/data/output/*.json`, published only on `127.0.0.1:8077` so only host nginx can reach it) and `pipeline` (one-shot, `profiles: [tools]`, invoked by host cron). Host nginx terminates TLS for `fisc.159-69-91-118.sslip.io` (Let's Encrypt via certbot, same pattern as your existing vhosts) and reverse-proxies to `127.0.0.1:8077`. Abuse is bounded by in-app slowapi rate limiting + the existing UFW firewall.

---

## File map (created at `/home/arnobgr/french-efficiency-dashboard/`)

| File | Responsibility |
|------|----------------|
| `Dockerfile` | Build one image containing the backend (used by both `api` and `pipeline`) |
| `.dockerignore` | Keep `.venv`, `data`, `.git`, frontend, docs out of the build context |
| `docker-compose.yml` | Define `api` + `pipeline` services (no caddy) |
| `.env` | Operator-supplied, gitignored: `ALLOWED_ORIGINS`, `RATE_LIMIT` |

Plus one file at `/etc/nginx/sites-available/fiscoscope` (the nginx vhost — created in Phase 2).

---

## Phase 0: Preflight

- [x] **Step 0.1: Confirm Docker usable as `arnobgr`** (no sudo)

```bash
docker --version
docker compose version
docker ps
```
Expected: versions print and `docker ps` lists the three existing containers (artstamp-api-1, situation-room-api, wristshotai_bot) — no permission error.

- [x] **Step 0.2: Confirm host port 8077 is free**

```bash
sudo ss -ltnp 'sport = :8077'
```
Expected: **no output**. (8077 is what the api container will bind to on localhost. `:8000` is held by artstamp; don't reuse it.)

- [x] **Step 0.3: Confirm the new sslip.io hostname resolves**

```bash
getent hosts fisc.159-69-91-118.sslip.io
```
Expected: a line showing `159.69.91.118`. (sslip.io resolves any subdomain whose label embeds the dashed IP.)

- [x] **Step 0.4: Confirm nginx, certbot.timer, and docker are running**

```bash
systemctl is-active nginx certbot.timer docker
```
Expected: three `active` lines.

- [x] **Step 0.5: Confirm the repo and branch**

```bash
su - arnobgr
cd /home/arnobgr/french-efficiency-dashboard
git status
git branch --show-current
git log -1 --oneline
```
Expected: clean working tree (or at least no surprises), on the branch you intend to deploy (likely `dev` per CLAUDE.md).

- [ ] **Step 0.6: Decide the Cloudflare Pages project name** (used in Phase 5). Suggest `fiscoscope`. Note your choice.

---

## Phase 1: Create the deployment files

All files at `/home/arnobgr/french-efficiency-dashboard/`.

- [x] **Step 1.1: Create `Dockerfile`**

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
# --proxy-headers + --forwarded-allow-ips=127.0.0.1 let uvicorn trust nginx's
# X-Forwarded-For so slowapi rate-limits on the real client IP. We restrict
# to 127.0.0.1 (not "*") because the container is bound to 127.0.0.1:8077
# on the host, so the only legitimate upstream is host nginx.
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
```

- [x] **Step 1.2: Create `.dockerignore`**

```
backend/.venv
backend/data
**/__pycache__
*.pyc
.git
frontend
docs
```

- [x] **Step 1.3: Create `docker-compose.yml`** (no caddy; api bound to `127.0.0.1:8077`)

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
      - ./backend/data:/app/data
    ports:
      - "127.0.0.1:8077:8000"   # localhost-only — host nginx is the only client

  pipeline:
    build: .
    image: fiscoscope-backend
    profiles: ["tools"]          # never starts with `up`; run on demand / via cron
    volumes:
      - ./backend/data:/app/data
    entrypoint: ["python", "run_pipeline.py"]
```

- [x] **Step 1.4: Create `.env`** (gitignored — do NOT commit). The Pages URL gets filled in for real in Phase 5; for now, use a placeholder that matches your intended project name:

```
ALLOWED_ORIGINS=https://fiscoscope.pages.dev
RATE_LIMIT=60/minute
```

- [x] **Step 1.5: Verify `.env` is gitignored**

```bash
cd /home/arnobgr/french-efficiency-dashboard
git check-ignore .env && echo "OK: .env is gitignored"
```
Expected: `.env` printed, then `OK: .env is gitignored`.

- [x] **Step 1.6 (recommended): Commit the deployment files**

```bash
git add Dockerfile .dockerignore docker-compose.yml
git commit -m "deploy: docker stack (api + pipeline) for host-nginx reverse proxy"
```

---

## Phase 2: nginx vhost + Let's Encrypt cert

This replaces the original plan's Caddy phases. Pattern matches your existing `situation-room` vhost exactly.

- [x] **Step 2.1: Create the HTTP-only vhost** (certbot will rewrite it to add TLS in step 2.3)

```bash
sudo tee /etc/nginx/sites-available/fiscoscope >/dev/null <<'NGINX'
server {
    listen 80;
    server_name fisc.159-69-91-118.sslip.io;

    location / {
        proxy_pass http://127.0.0.1:8077;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX
```

- [x] **Step 2.2: Enable the vhost and reload nginx**

```bash
sudo ln -s /etc/nginx/sites-available/fiscoscope /etc/nginx/sites-enabled/fiscoscope
sudo nginx -t
sudo systemctl reload nginx
```
Expected: `nginx: configuration file /etc/nginx/nginx.conf test is successful`, then a clean reload.

- [x] **Step 2.3: Obtain the TLS cert and have certbot rewrite the vhost for HTTPS**

```bash
sudo certbot --nginx -d fisc.159-69-91-118.sslip.io
```
Answer prompts:
- Email: your email (only the first time).
- Agree to ToS: yes.
- Share email with EFF: your call.
- Redirect HTTP → HTTPS: **yes** (option 2). Matches the existing vhosts.

Expected: certbot reports the cert was obtained, writes `listen 443 ssl` and the cert paths into the vhost, adds an HTTP→HTTPS 301 server block, and reloads nginx.

- [x] **Step 2.4: Verify the cert renewal will work**

```bash
sudo certbot certificates | grep -A2 fisc.159-69-91-118.sslip.io
sudo certbot renew --dry-run 2>&1 | tail -20
```
Expected: the new cert listed; dry-run reports `Congratulations, all simulated renewals succeeded` (or that no certs were near expiry — both are fine). `certbot.timer` will keep it renewed automatically.

---

## Phase 3: Build and launch the api container

- [ ] **Step 3.1: Build and start `api`** (NOT pipeline — that's tools-profile, on demand)

```bash
cd /home/arnobgr/french-efficiency-dashboard
docker compose up -d --build api
```
Expected: image builds; one container starts.

- [ ] **Step 3.2: Confirm container state + port binding**

```bash
docker compose ps
sudo ss -ltnp 'sport = :8077'
```
Expected: `api` is `running`. The `ss` line shows docker-proxy listening on `127.0.0.1:8077` (NOT `0.0.0.0:8077` — if it shows `0.0.0.0`, fix the `ports:` line and `docker compose up -d` again).

- [ ] **Step 3.3: Hit the API directly on localhost** (skipping nginx)

```bash
curl -s http://127.0.0.1:8077/healthz; echo
```
Expected: `{"status":"ok"}`.

- [ ] **Step 3.4: Hit the API through nginx over HTTPS**

```bash
curl -s --retry 10 --retry-delay 2 --retry-connrefused https://fisc.159-69-91-118.sslip.io/healthz; echo
```
Expected: `{"status":"ok"}` over valid TLS (no curl cert warnings). Public HTTPS is now live.

---

## Phase 4: Populate data + schedule the pipeline

The `api` serves `backend/data/output/*.json`. If empty (first time), run the pipeline once, then schedule it.

- [ ] **Step 4.1: Run the pipeline once**

```bash
cd /home/arnobgr/french-efficiency-dashboard
docker compose run --rm pipeline --mode full
```
Expected: log lines for each fetcher/processor; ends with `Pipeline complete`. Some sources may log `skipped`/`error` (fail-soft by design, e.g. expired Urssaf TLS cert) — that's fine as long as it finishes. Files land in `./backend/data/output/` (owned by root since the container writes as root — readable from the host; use `sudo` if you ever need to edit/delete them directly).

- [ ] **Step 4.2: Confirm the live API serves the fresh data**

```bash
curl -s https://fisc.159-69-91-118.sslip.io/api/kpis; echo
curl -s https://fisc.159-69-91-118.sslip.io/api/meta | head -c 200; echo
```
Expected: `{"kpis":[...]}` listing the KPI files, and a `meta` payload whose `last_run` is recent.

- [ ] **Step 4.3: Schedule periodic refreshes with cron**

```bash
crontab -e
```
Add these two lines (cron has a minimal PATH, so the absolute `docker` path and the `cd` are required):

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
Expected: the two lines above. (No sudo: you run `docker` directly via the docker group.)

- [ ] **Step 4.5: Ensure Docker starts on boot** (so the api container comes back after a reboot; `restart: unless-stopped` then keeps it alive)

```bash
sudo systemctl is-enabled docker
```
Expected: `enabled`. (If `disabled`, run `sudo systemctl enable docker`.)

---

## Phase 5: Cloudflare Pages (reserve the frontend origin + wire CORS)

The frontend isn't built yet (Phase 2 of the project). Reserve the `*.pages.dev` subdomain now and point CORS at it so it's ready.

- [ ] **Step 5.1: Create a placeholder site**

```bash
mkdir -p /tmp/fisc-placeholder && printf '<!doctype html><title>fiscoscope</title><h1>fiscoscope — coming soon</h1>\n' > /tmp/fisc-placeholder/index.html
```

- [ ] **Step 5.2: Create the Pages project**

1. Log in at `https://dash.cloudflare.com` (free account).
2. Left sidebar → **Workers & Pages** → **Create** → **Pages** tab → **Upload assets**.
3. Project name: the name from Step 0.6 (`fiscoscope`).
4. Drag in `index.html` (or the folder) → **Deploy**.

CLI alternative: `npx wrangler pages deploy /tmp/fisc-placeholder --project-name fiscoscope`.

- [ ] **Step 5.3: Capture the real production URL**

```bash
curl -sI https://fiscoscope.pages.dev | head -1
```
Expected: `HTTP/2 200`. If Cloudflare appended a suffix because the name was taken, use the actual URL.

- [ ] **Step 5.4: Point the API's CORS allowlist at that URL**

If the URL differs from the placeholder in `.env`, edit it:

```bash
cd /home/arnobgr/french-efficiency-dashboard
# update ALLOWED_ORIGINS in .env to the exact Pages URL (scheme + host, no trailing slash)
nano .env
```

Then recreate the `api` container so it picks up the new env (plain `restart` does NOT reload env — must use `up -d`):

```bash
docker compose up -d api
```

- [ ] **Step 5.5: Verify the CORS header is returned for that origin**

```bash
curl -sI -H "Origin: https://fiscoscope.pages.dev" https://fisc.159-69-91-118.sslip.io/api/meta | grep -i access-control-allow-origin
```
Expected: `access-control-allow-origin: https://fiscoscope.pages.dev`. A different/absent origin should NOT be echoed.

---

## Phase 6: Final verification + ongoing ops

- [ ] **Step 6.1: End-to-end check**

```bash
curl -s https://fisc.159-69-91-118.sslip.io/healthz; echo
curl -s https://fisc.159-69-91-118.sslip.io/api/kpis; echo
curl -s -o /dev/null -w "missing -> %{http_code}\n" https://fisc.159-69-91-118.sslip.io/api/kpi/nope
```
Expected: `{"status":"ok"}`, the KPI list, and `missing -> 404`.

- [ ] **Step 6.2: Confirm the stack survives a restart**

```bash
docker compose restart
docker compose ps
curl -s --retry 10 --retry-delay 2 https://fisc.159-69-91-118.sslip.io/healthz; echo
```
Expected: container comes back `running`; healthz returns ok. (nginx and the cert are untouched — they live on the host, not in docker.)

- [ ] **Step 6.3: Confirm nothing else broke**

```bash
curl -sI https://159.69.91.118.sslip.io | head -1                  # artstamp
curl -sI https://situation-room.159-69-91-118.sslip.io | head -1   # situation-room
```
Expected: both still respond (`HTTP/2 200` or whatever each app normally returns).

### Operations cheat-sheet

- **Logs:** `docker compose logs -f api`, and `sudo journalctl -u nginx -f` for the proxy side.
- **Deploy code changes:** `cd /home/arnobgr/french-efficiency-dashboard && git pull && docker compose up -d --build api`.
- **Manual data refresh:** `docker compose run --rm pipeline --mode full`.
- **Pipeline cron logs:** `tail -f /home/arnobgr/fisc-pipeline.log`.
- **Cert renewal:** automatic via `certbot.timer` (already running; no action needed).
- **nginx vhost changes:** edit `/etc/nginx/sites-available/fiscoscope`, then `sudo nginx -t && sudo systemctl reload nginx`.
- **When the real frontend exists:** set its API base URL to `https://fisc.159-69-91-118.sslip.io/api`, redeploy to the same Pages project (keeping the same origin so `ALLOWED_ORIGINS` still matches), or wire the Pages project to git for auto-deploys.

---

## What changed vs. the 2026-05-22 plan

| Concern | Original plan | This adapted plan |
|---|---|---|
| Reverse proxy | Caddy in docker, owning 80/443 | Existing host nginx, third vhost |
| TLS issuance | Caddy auto-ACME | `certbot --nginx` (matches your existing vhosts) |
| Hostname | `<dashed-ip>.sslip.io` | `fisc.159-69-91-118.sslip.io` (bare form is taken by artstamp) |
| api container exposure | `expose: 8000` (compose network only) | `ports: "127.0.0.1:8077:8000"` (host-loopback only) |
| Caddyfile | yes | none |
| `.env` `SITE_ADDRESS` | yes | dropped (nginx owns hostname routing) |
| Firewall | new ufw rules for 80/443 | no changes — already correct |
| SSH lockout warning | applies | already mitigated (your 22 rule is tailnet-only) |
| Cloudflare Pages + CORS | same | same |
| Pipeline cron | same | same |

## What stayed identical

- `Dockerfile`, `.dockerignore`, the `pipeline` service definition.
- Phase 4 (pipeline run + cron schedule).
- Phase 5 (Cloudflare Pages + CORS).
- Operational patterns (logs, deploy, refresh).

## Known side observations (not blocking, worth knowing)

- `artstamp-api-1` publishes on `0.0.0.0:8000` (publicly reachable, bypassing nginx + TLS — Docker's port publishing skirts UFW on Ubuntu by default). Not our problem today, but you may want to change that container's mapping to `127.0.0.1:8000:8000` eventually.
- `tailscale debug prefs` shows `ShieldsUp: false` — anyone on your tailnet can reach the VPS's ports over Tailscale. Fine for the public API; just context.
