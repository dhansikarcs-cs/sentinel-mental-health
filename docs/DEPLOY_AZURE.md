# Deploying Sentinel to Microsoft Azure

Sentinel ships with everything needed to run on Azure. Three supported paths:

| Path | What you get | Best for |
|------|--------------|----------|
| **A. Code deploy, no Docker** (simplest) | GitHub Actions zip-deploys the Python app + built frontend; Oryx pip-installs on the server | **Default.** Fastest way to get a live site, no registry, 2 GitHub secrets |
| **B. Single App Service container** | One container = API + frontend + SQLite | Parity with local Docker, self-contained image |
| **C. Container Apps / two App Services** | API + Postgres + scheduler, nginx fronts the API | Production / multi-user |

> ⚠️ **App Service must run the PYTHON runtime, not Node.** Sentinel is a FastAPI (Python)
> backend that serves the built React frontend itself. If your App Service was created with a
> Node.js runtime stack, you'll only ever see Azure's default "Your web app is running and
> waiting for your content — Built with NodeJS" placeholder page. Node startup commands
> (`node server.js`, `npm run start`, `pm2 serve dist`) do **not** apply — there is no Node
> entry point. See Path A step 1 to switch the runtime stack.

---

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az`) — optional for Path A, required for B/C
- [Docker](https://docs.docker.com/get-docker/) (only for paths B and C; path A builds on GitHub Actions)
- An Azure subscription ([free tier](https://azure.microsoft.com/free/) works)

---

## Path A — Code deploy, no Docker (simplest)

GitHub Actions packages the backend + freshly built frontend into a zip and deploys it to
App Service with a **publish profile**. On the server, Oryx creates a virtualenv
(`antenv`) and pip-installs `backend/requirements.txt`. One App Service hosts the whole
app (API + SPA + SQLite). The deploy job lives in `.github/workflows/ci.yml` → `deploy`.

### 1. Point the App Service at Python (one-time)

If the app was created with a Node.js (or other code) runtime stack, switch it to Python —
Linux App Service locks the stack type in the portal after creation, so use the CLI:

```bash
az webapp config set -g <resource-group> -n <app-name> --linux-fx-version "PYTHON|3.12"
```

(Or simply delete the web app and recreate it in the portal with **Runtime stack: Python 12**,
Linux, B1 — same result.)

### 2. Set the Startup Command

Portal → App Service → **Configuration → General settings → Startup command**:

```
bash /home/site/wwwroot/azure-startup.sh
```

That script redirects SQLite to persistent `/home/data/`, seeds the demo clinic exactly
once, and starts uvicorn on the correct port. It is shared with the Docker path (Path B).

### 3. Set the required App Service environment variables

Portal → **Configuration → Environment variables** (or CLI):

```bash
az webapp config appsettings set --resource-group <rg> --name <app-name> --settings \
  JWT_SECRET="$(openssl rand -hex 32)" \
  ENCRYPTION_PASSPHRASE="$(openssl rand -base64 32)" \
  ENCRYPTION_SALT="$(openssl rand -hex 16)" \
  ENCRYPTION_REQUIRED=true \
  COOKIE_SECURE=true \
  CORS_ORIGINS="https://<app-name>.azurewebsites.net" \
  SENTINEL_ACK_LINK="https://<app-name>.azurewebsites.net/trustee" \
  TRUSTEE_LINK_SECRET="$(openssl rand -hex 32)" \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  SEED_DEMO=true
```

> **Never change `ENCRYPTION_PASSPHRASE` or `ENCRYPTION_SALT` after the first deploy** —
> journal data becomes undecryptable if they change.
>
> Without `JWT_SECRET` / `ENCRYPTION_PASSPHRASE` the app deliberately refuses to boot —
> if the site 502s after deploy, this is the first thing to check in Log Stream.

Optional AI + email settings: see the environment variable reference below.

#### Enabling the AI Companion (Foundry agent)

To turn on the AI Companion chat backed by your Foundry hosted agent, add:

```bash
az webapp config appsettings set --resource-group <rg> --name <app-name> --settings \
  AZURE_AGENT_ENDPOINT="https://wispernote.services.ai.azure.com/api/projects/wispernote" \
  AZURE_AGENT_NAME="Sentinelagent" \
  AZURE_AGENT_VERSION="1" \
  AZURE_AGENT_MODE="auto"
```

Auth is the app's **managed identity** (enabled by default on App Service) — grant it the
**Azure AI User** role on the wispernote resource (Portal → wispernote → Access control
(IAM) → Add role assignment → Managed identity → your app). Without those settings the
Companion still works in offline supportive-fallback mode.

### 4. Add the two GitHub secrets

| Secret | How to get it |
|--------|---------------|
| `AZURE_WEBAPP_NAME` | The App Service name, e.g. `sentinelphyc-f5htbzb4dketg7hk` |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | Portal → App Service → **Overview → Download publish profile**, then paste the downloaded `.PublishSettings` XML as the secret value |

Then re-run the workflow (GitHub → Actions → Sentinel CI/CD → **Run workflow**), or push to `main`.

The job fails fast with an actionable message if either secret is missing, and finishes
with a live `/health` smoke test.

### 5. Open it

```
https://<app-name>.azurewebsites.net
```

Health check: `https://<app-name>.azurewebsites.net/health`

### Deploying without git — VS Code App Service extension

Not using git/Actions? Deploy the `azure-deploy/` folder instead:

1. Run `sh build-azure-deploy.sh` (repo root) — builds the frontend and stages
   `azure-deploy/` (backend + dist + `.deployment` + `azure-startup.sh`).
2. `.vscode/settings.json` already points `appService.deploySubpath` at `azure-deploy`,
   so in the VS Code Azure panel: right-click your web app → **Deploy to Web App…**.
3. First deploy takes several minutes (Oryx pip-installs `requirements.txt` on the server).

The web app itself still needs Path A steps 1–3 (Python runtime stack, startup
command, app settings) — those are configured once on the Azure side.

---

## Path B — Single App Service (one Docker container, everything included)

`main.py` already serves the built `frontend/dist` as an SPA, so one container hosts
the whole app. `Dockerfile.azure` (repo root) builds it.

### 1. Create a resource group + registry

```bash
az group create --name sentinel-rg --location westus2

az acr create --resource-group sentinel-rg --name <your-registry> --sku Basic --admin-enabled true
```

### 2. Build & push the image

```bash
# from the repo root
az acr build --registry <your-registry> --image sentinel:latest --file Dockerfile.azure .
```

### 3. Create the App Service plan + web app

```bash
az appservice plan create --resource-group sentinel-rg --name sentinel-plan --is-linux --sku B1

az webapp create \
  --resource-group sentinel-rg \
  --plan sentinel-plan \
  --name <your-app-name> \
  --container-image <your-registry>.azurecr.io/sentinel:latest
```

### 4. Configure the container port

```bash
az webapp config appsettings set --resource-group sentinel-rg --name <your-app-name> --settings WEBSITES_PORT=8000
```

### 5. Set the required environment variables

```bash
az webapp config appsettings set --resource-group sentinel-rg --name <your-app-name> --settings \
  JWT_SECRET="$(openssl rand -hex 32)" \
  ENCRYPTION_PASSPHRASE="$(openssl rand -base64 32)" \
  ENCRYPTION_SALT="$(openssl rand -hex 16)" \
  ENCRYPTION_REQUIRED=true \
  COOKIE_SECURE=true \
  CORS_ORIGINS="https://<your-app-name>.azurewebsites.net" \
  SENTINEL_ACK_LINK="https://<your-app-name>.azurewebsites.net/trustee" \
  TRUSTEE_LINK_SECRET="$(openssl rand -hex 32)" \
  RUN_WORKERS=true \
  RATE_LIMIT_BACKEND=memory
```

> **Never change `ENCRYPTION_PASSPHRASE` or `ENCRYPTION_SALT` after the first deploy** —
> journal data becomes undecryptable if they change.

Optional integrations (AI + email) — see the table below for where to get each value:

```bash
az webapp config appsettings set --resource-group sentinel-rg --name <your-app-name> --settings \
  AZURE_AI_ENDPOINT="https://<your-foundry-or-openai>.services.ai.azure.com" \
  AZURE_AI_KEY="<your-azure-ai-key>" \
  AZURE_DEPLOYMENT="gpt-4o-mini" \
  ALLOW_CLOUD_AI=true \
  SMTP_HOST=smtp.gmail.com \
  SMTP_PORT=587 \
  SMTP_USER="you@gmail.com" \
  SMTP_PASSWORD="<gmail-app-password>" \
  EMAIL_FROM="Sentinel <you@gmail.com>" \
  CRISIS_HELPLINE_EMAIL="helpline@yourclinic.org"
```

### 6. Startup command & demo data

Leave **Startup command empty** — the image's `CMD` runs `/app/azure-startup.sh`, which:

1. **Redirects SQLite to persistent storage** (`sqlite:////home/data/sentinel.db`). `/home` is the
   persistent App Service mount — without this, the database is wiped on every restart/scale event.
2. **Seeds the demo clinic exactly once**, guarded by a marker file (`/home/data/.demo-seeded`).
   Unlike running `seed_clinic.py` directly (which **wipes all data** on every run), the startup
   script never destroys existing data on restarts.
3. **Starts uvicorn** on the port App Service expects (`WEBSITES_PORT` → `PORT` → 8000).

Don't want the demo accounts in production? Set `SEED_DEMO=false` in App Service settings.

### 7. Open it

```
https://<your-app-name>.azurewebsites.net
```

Health check: `https://<your-app-name>.azurewebsites.net/health`

---

## Path C — Container Apps (API + nginx frontend + Postgres + scheduler)

Use this when you want PostgreSQL, horizontal scaling, and a dedicated worker for
reminder/celebration loops. `frontend/nginx.conf` proxies `/api/*` to the backend
(this was fixed — the old config stripped the prefix and broke every API call).

### 1. Database — Azure Database for PostgreSQL

```bash
az postgres flexible-server create \
  --resource-group sentinel-rg \
  --name sentinel-pg \
  --admin-user sentinel \
  --admin-password "<strong-password>" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --public-access All

az postgres flexible-server db create \
  --resource-group sentinel-rg \
  --server-name sentinel-pg \
  --database-name sentinel
```

Connection string (for `DATABASE_URL`):

```
postgresql://sentinel:<password>@sentinel-pg.postgres.database.azure.com:5432/sentinel?sslmode=require
```

### 2. Backend image

```bash
az acr build --registry <your-registry> --image sentinel-api:latest --file backend/Dockerfile backend
```

### 3. Frontend image (build-arg points nginx at the API)

```bash
az acr build --registry <your-registry> --image sentinel-web:latest \
  --build-arg BACKEND_URL=https://<api-app-name>.azurecontainerapps.io frontend
```

### 4. Deploy with Container Apps

```bash
az containerapp env create --name sentinel-env --resource-group sentinel-rg --location westus2

az containerapp create \
  --name sentinel-api \
  --resource-group sentinel-rg \
  --environment sentinel-env \
  --image <your-registry>.azurecr.io/sentinel-api:latest \
  --target-port 8000 --ingress external \
  --secrets pg-url="<DATABASE_URL>" \
  --env-vars DATABASE_URL=secretref:pg-url \
             JWT_SECRET="$(openssl rand -hex 32)" \
             ENCRYPTION_PASSPHRASE="<passphrase>" \
             ENCRYPTION_SALT="<salt-hex>" \
             RUN_WORKERS=false \
             RATE_LIMIT_BACKEND=db \
             WS_PUBSUB=auto \
             COOKIE_SECURE=true \
             CORS_ORIGINS="https://<web-app-name>.azurecontainerapps.io"

az containerapp create \
  --name sentinel-web \
  --resource-group sentinel-rg \
  --environment sentinel-env \
  --image <your-registry>.azurecr.io/sentinel-web:latest \
  --target-port 10000 --ingress external

# scheduler (internal only — no ingress)
az containerapp create \
  --name sentinel-scheduler \
  --resource-group sentinel-rg \
  --environment sentinel-env \
  --image <your-registry>.azurecr.io/sentinel-api:latest \
  --ingress internal --target-port 8000 \
  --secrets pg-url="<DATABASE_URL>" \
  --env-vars DATABASE_URL=secretref:pg-url \
             RUN_WORKERS=true \
             ENCRYPTION_PASSPHRASE="<passphrase>" \
             ENCRYPTION_SALT="<salt-hex>"
```

The scheduler uses a Postgres advisory lock, so you can scale it to 2+ replicas and
exactly one stays active (failover-safe).

---

## CI/CD — deploy on every push to `main`

`.github/workflows/ci.yml` deploys automatically after lint/tests/builds pass (Path A,
no Docker). Configure these GitHub repository secrets once:

| Secret | How to get it |
|--------|---------------|
| `AZURE_WEBAPP_NAME` | Your App Service name (e.g. `sentinelphyc-f5htbzb4dketg7hk`) |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | Portal → App Service → Overview → **Download publish profile** → paste the XML file's contents |

The deploy job verifies both secrets up front (clear error if missing), zip-deploys the
package, and ends with a `/health` smoke test against the live site. You can also trigger
it manually from the Actions tab ("Run workflow").

Prefer the Docker path (Path B) in CI instead? Point `azure/webapps-deploy@v3` at your
ACR image — you'll need an App Registration with OIDC federation, `AcrPush` on the
registry, and `Website Contributor` on the web app (see Path B steps 1–2).

---

## Data persistence on App Service (SQLite)

The startup script points SQLite at `/home/data/` — the only persistent path on
Linux App Service. Everything else (container filesystem) resets on restart,
redeploy, or scale-out. Uploaded files (consent forms, followup attachments) also
land under the app's data paths — keep `DATABASE_URL` unset and let the script
manage it. If you outgrow SQLite (multi-instance, heavy writes), switch to
Path C with Azure Database for PostgreSQL and set `DATABASE_URL` explicitly.

---

## Environment variable reference

| Variable | Required | Notes |
|----------|----------|-------|
| `JWT_SECRET` | **Yes** | Long random string; app refuses to boot with the default |
| `ENCRYPTION_PASSPHRASE` | **Yes** | Set once, never change (journal encryption) |
| `ENCRYPTION_SALT` | **Yes** | 32 hex chars; set once, never change |
| `ENCRYPTION_REQUIRED` | Yes | `true` in production |
| `DATABASE_URL` | Path C | `postgresql://...?sslmode=require` |
| `COOKIE_SECURE` | Yes | `true` behind HTTPS |
| `CORS_ORIGINS` | Yes | Public frontend URL, comma-separated |
| `SENTINEL_ACK_LINK` | Yes | Absolute trustee callback URL |
| `TRUSTEE_LINK_SECRET` | Yes | Random hex string |
| `RUN_WORKERS` | Path C | `false` on API, `true` on scheduler |
| `SEED_DEMO` | Optional | `false` to skip demo accounts on first boot (default `true`) |
| `RATE_LIMIT_BACKEND` | Path C | `db` when running multiple API processes |
| `AZURE_AI_ENDPOINT` / `AZURE_AI_KEY` | Optional | Azure AI Foundry or Azure OpenAI |
| `AZURE_DEPLOYMENT` | Optional | Deployment/model name (default `gpt-4o-mini`) |
| `AZURE_AGENT_ENDPOINT` / `AZURE_AGENT_NAME` | Optional | Foundry hosted agent for the AI Companion (e.g. `https://wispernote.services.ai.azure.com/api/projects/wispernote` + `Sentinelagent`) |
| `AZURE_AGENT_VERSION` / `AZURE_AGENT_MODE` | Optional | Pin agent version (`1`, or empty = latest); `auto` (after Ollama) / `on` (first) / `off` |
| `ALLOW_CLOUD_AI` | Optional | `true` to let AI fall back past local Ollama |
| `GROQ_API_KEY` | Optional | Free cloud AI fallback |
| `SMTP_*`, `EMAIL_FROM`, `CRISIS_HELPLINE_EMAIL` | Optional | Crisis escalation email |
| `OLLAMA_URL`, `OLLAMA_MODEL` | Optional | Local Ollama (usually skipped on Azure) |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Azure shows the default "Your web app is running and waiting for your content — Built with NodeJS" page | The App Service is an empty Node **code** app — nothing was ever deployed (or the deploy job failed on missing secrets). Switch the runtime to Python (Path A step 1), set the startup command (Path A step 2), add the two GitHub secrets, and redeploy. Node startup commands (`node server.js`, `npm run start`, `pm2 serve`) don't apply — Sentinel is Python. |
| GitHub Actions deploy job fails on the preflight step | `AZURE_WEBAPP_NAME` / `AZURE_WEBAPP_PUBLISH_PROFILE` secrets are missing — see Path A step 4. |
| Container starts then stops | Missing `JWT_SECRET` or `ENCRYPTION_PASSPHRASE` — the app refuses to start with defaults. Check Log Stream. |
| Frontend loads, API calls 404 | Make sure the nginx config was rebuilt after the `/api` prefix fix (`proxy_pass ${BACKEND_URL};` — no trailing slash). |
| Logs show `sqlite: unable to open database file` | Path A/B: make sure the startup command runs `azure-startup.sh` — it points SQLite at the writable `/home/data` mount (container path: the Dockerfile pre-creates `/app/data`). Path C: you're on SQLite — switch to PostgreSQL. |
| Login works, then 401s | `COOKIE_SECURE=true` requires HTTPS — confirm you're browsing the https:// URL. |
| AI summaries missing | `ALLOW_CLOUD_AI` is false and no Ollama is reachable — set Azure/Groq keys or accept rule-based fallback. |
| Slow first load | B1 tier cold start; consider B2 or always-on in Configuration → General. |
