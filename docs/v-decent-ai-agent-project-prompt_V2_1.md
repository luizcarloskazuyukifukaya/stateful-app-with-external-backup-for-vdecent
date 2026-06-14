# V-Decent AI Coding Agent Project Prompt

**Prompt version:** 2.1  
**Based on:** V-Decent Application Development Guide (en, V2.1)  
**Audience:** Human developers using AI coding agents such as Codex, Gemini CLI, Claude Code, Cursor, or similar tools.

Use this prompt when starting or updating an application project intended to run on **V-Decent Virtual Distributed Infrastructure**, also called **V-Decent**.

---

## Prompt to Give the AI Coding Agent

You are an expert full-stack application developer. Build this application so it can be developed, tested, registered, handed over, and deployed through **V-Decent Virtual Distributed Infrastructure**.

V-Decent is a distributed datacenter hosting environment that uses **Docker Compose**, **Cloudflare Tunnels**, **Coolify orchestration**, a shared ingress network, and the **V-Decent Application Manager**. The application must be compatible with V-Decent deployment rules from the beginning.

Your job is to create production-ready application code, repository structure, Docker configuration, environment-variable templates, local test instructions, and deployment handover notes.

The project must follow the V-Decent Application Development Guide **V2.1**.

---

## Application to Build

Replace the placeholders below before starting:

```text
Application name: <APP_NAME>
Primary shortname / subdomain: <APP_SHORTNAME>
Target production URL: https://<APP_SHORTNAME>.v-decent.org
Application type: <STATELESS | STATEFUL_EXTERNAL_DATA | STATEFUL_WITH_LIMITED_INTERNAL_DATA>
Main application purpose: <DESCRIBE_THE_APP>
Technology stack preference: <NODE/EXPRESS | NEXT.JS | PYTHON/FASTAPI | OTHER>
Primary exposed service/container: <SERVICE_NAME>
Internal application port: <PORT>
External storage required: <YES/NO>
Database required: <YES/NO>
Backup sidecar required: <YES/NO>
Repository visibility: <PUBLIC | PRIVATE>
Git branch for deployment: <BRANCH_NAME>
Developer group: <DEVELOPER_GROUP>
GitHub account or organization: <GITHUB_ACCOUNT_OR_ORG>
```

---

## Non-Negotiable V-Decent Compatibility Rules

The repository must be compatible with V-Decent Application Manager and Coolify deployment.

### 1. Docker Compose Is Required

Create a file named exactly:

```text
docker-compose.yaml
```

Do not use a different file name such as `docker-compose.yml`, `compose.yaml`, or `docker-compose.prod.yaml` as the only deployment manifest.

The Docker Compose file must define every service needed by the application.

---

### 2. Do Not Use Host Port Mapping in the Primary Manifest

Do **not** use host port mappings like this in the primary V-Decent deployment manifest:

```yaml
ports:
  - "8080:80"
```

V-Decent handles ingress routing through Cloudflare Tunnels, the Coolify proxy, and the shared V-Decent ingress network. Services that need to receive external traffic must use `expose`, not `ports`.

Use this pattern:

```yaml
services:
  app:
    build: .
    restart: always
    expose:
      - "80"
    environment:
      - PORT=80
```

For local-only testing, host port mapping may be placed in a separate override file such as:

```text
docker-compose.local.yaml
```

The main `docker-compose.yaml` must remain V-Decent compatible and must not depend on host port mappings.

---

### 3. Public Web Service Must Join `vdecent-ingress`

In V-Decent Guide V2.1, the public-facing service container must join the platform's pre-existing shared external network:

```text
vdecent-ingress
```

This lets the node proxy discover and safely route traffic to the application.

The public-facing service should include both its private/internal app network and the shared ingress network:

```yaml
services:
  app:
    build: .
    restart: always
    expose:
      - "80"
    networks:
      - app-network
      - vdecent-ingress
    labels:
      - "coolify.managed=true"

networks:
  app-network:
    driver: bridge
  vdecent-ingress:
    external: true
    name: vdecent-ingress
```

Internal services such as databases, workers, queues, and backup sidecars must **not** join `vdecent-ingress` unless there is an explicit V-Decent Operator-approved reason.

---

### 4. Exactly One Public-Facing Service Unless Specified Otherwise

Identify which service should be exposed by V-Decent Application Manager.

Most applications should expose only the main web/API container, for example:

```text
Expose: app -> https://<APP_SHORTNAME>.v-decent.org
Do not expose: db, redis, worker, backup-sidecar, internal services
```

If a service should not be reachable from the internet, its URL field must be left empty during V-Decent Application Manager registration.

---

### 5. Environment Variables Are Required

Use environment variables for runtime configuration. Provide:

```text
.env.example
```

The `.env.example` file must list all required variables with safe sample values or clear placeholders.

Never commit real production secrets.

Example:

```env
# App Configuration
PORT=80
SITE_NAME=Example V-Decent App
PRIMARY_COLOR=#1a73e8

# External Services
DATABASE_URL=postgres://user:password@db:5432/appdb
API_KEY=replace_me
```

Also provide a separate section in the README called **Production Environment Variables** explaining which values must be supplied to V-Decent Application Manager.

When registering the application, the developer must provide the actual production environment-variable values as part of the application information.

---

### 6. Health Checks Are Required

Add Docker health checks for services where possible, especially the main app and database.

Example for a web app:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:80/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 10
```

The application should expose a lightweight health endpoint:

```text
GET /health
```

The health endpoint should return HTTP 200 when the application is ready to receive traffic.

---

## Supported Application Types and Data Persistence Rules

V-Decent supports three application patterns. Choose one explicitly and document it in the README and handover document.

### Pattern A — Stateless Application

Use this when the app does not store persistent data inside the container or in V-Decent-managed storage.

Requirements:

```text
No local persistent data
No database volume
No uploads stored inside the container filesystem
All configuration through environment variables
The app can be redeployed or moved without data migration
```

---

### Pattern B — Stateful Application with External Data

Use this when the app stores data outside V-Decent, such as AWS S3, Wasabi, a managed database, or another external storage system.

Requirements:

```text
External data location configured by environment variables
No assumption that the container filesystem persists
Clear documentation of all external storage variables
Application stores only references/configuration required to reach external storage
```

---

### Pattern C — Stateful Application with Internal Data, Supported with Limitation

Use this only when a database or persistent volume is included in Docker Compose.

V-Decent Guide V2.1 clarifies that this pattern is supported with limitations and that backup/restore can be implemented using an external backup sidecar. Automated backups of the application, including the database, are supported when the application is packaged appropriately; however, database data is not guaranteed unless external backup/restore is properly configured.

Requirements:

```text
Map data to discrete Docker volumes
Document that database persistence is limited unless external backup is configured
Add database health checks
Do not expose the database service publicly
Keep databases and internal services isolated on an internal bridge network
If backup is required, include a backup sidecar container and document backup/restore behavior
Document external backup target, restore procedure, and limitations
```

V-Decent Guide V2.1 also notes support for data backup and restore to/from Google Drive, including point-in-time restore capability and persistence across node migration when the backup sidecar approach is used.

Developers planning stateful apps should prepare for current and future V-Decent data-management features by mapping application data to discrete Docker volumes.

---

## Recommended Docker Compose Baseline for V-Decent V2.1

Use this as the baseline structure for applications with a public app service and an internal database:

```yaml
services:
  app:
    build: .
    restart: always
    environment:
      - PORT=80
      - DATABASE_URL=postgres://user:password@db:5432/appdb
    expose:
      - "80"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:80/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks:
      - app-network
      - vdecent-ingress
    labels:
      - "coolify.managed=true"

  db:
    image: postgres:16-alpine
    restart: always
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d appdb"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
  vdecent-ingress:
    external: true
    name: vdecent-ingress

volumes:
  postgres_data:
```

For a stateless application without a database, remove the `db` service, `DATABASE_URL`, `depends_on`, and `postgres_data` volume, but keep the public app service connected to `vdecent-ingress`.

---

## Backup Sidecar Guidance for Stateful Apps

If the application uses internal persistent data and backup is required, include or document a backup sidecar container.

The sidecar should:

```text
Run as an internal-only service
Not expose any public URL
Not join vdecent-ingress unless explicitly approved
Use environment variables for external backup credentials and destination
Back up the database or data volumes to external storage
Document backup schedule, restore command, and point-in-time restore behavior if supported
```

Example handover fields for backup configuration:

```env
BACKUP_ENABLED=true
BACKUP_PROVIDER=google_drive
GOOGLE_CREDENTIALS_B64=replace_me
GOOGLE_TOKEN_B64=replace_me
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE_CRON=0 */6 * * *
```

Never commit real backup credentials or tokens.

---

## Required Repository Structure

Create or maintain this minimum structure:

```text
.
├── docker-compose.yaml
├── Dockerfile
├── .env.example
├── README.md
├── src/
│   └── ...
└── docs/
    └── vdecent-handover.md
```

You may adapt the structure for the selected framework, but the root-level `docker-compose.yaml`, `Dockerfile`, `.env.example`, and `README.md` are mandatory.

---

## Required README Sections

Create a `README.md` with these sections:

```markdown
# <APP_NAME>

## Overview
Describe what the application does.

## Technology Stack
List the language, framework, runtime, database, and external services.

## V-Decent Compatibility
Explain that the app is designed for V-Decent deployment.

Include:
- Docker Compose file: `docker-compose.yaml`
- No host port mappings in the primary manifest
- Public-facing service name
- Internal exposed port
- Public-facing service joins `vdecent-ingress`
- Internal services do not join `vdecent-ingress`
- Health endpoint
- Docker health checks
- Environment variable configuration
- Stateful/stateless classification
- Backup sidecar status, if applicable

## Local Development

### 1. Copy Environment File
```bash
cp .env.example .env
```

### 2. Build and Start
```bash
docker compose up --build
```

### 3. Test Health
```bash
curl http://localhost:<LOCAL_TEST_PORT>/health
```

If local testing needs host port mapping, create a separate local-only compose override file, such as `docker-compose.local.yaml`. Do not depend on host port mapping in the main `docker-compose.yaml`.

## Production Environment Variables
List every variable required by V-Decent Application Manager.

## Deployment Source
Repository URL:
Branch:
Repository visibility:

## V-Decent Application Manager Registration Notes
Public-facing service:
Production URL:
Internal services that must not be exposed:
Services that must remain isolated from `vdecent-ingress`:

## Data Persistence and Backup
Application type:
External storage:
Docker volumes:
Backup sidecar:
Backup target:
Restore procedure:
Known limitations:

## Troubleshooting
Explain common startup, health check, database, backup, ingress-network, and environment-variable issues.
```

---

## Required Handover Document

Create:

```text
docs/vdecent-handover.md
```

It must include:

```markdown
# V-Decent Deployment Handover

## Application Identity
Application name:
Primary shortname:
Production URL:
Developer group:
GitHub account or organization:

## Deployment Source
Repository URL:
Repository visibility:
Branch:
Manifest file: docker-compose.yaml

## Service Exposure
| Service | Expose Publicly? | URL | Networks | Notes |
|---|---:|---|---|---|
| app | Yes | https://<APP_SHORTNAME>.v-decent.org | app-network, vdecent-ingress | Main web/API service |
| db | No |  | app-network | Internal database only |
| backup-sidecar | No |  | app-network | Internal backup service, if used |

## Environment Variables for Production
```env
PORT=80
...
```

## Health Check
Health endpoint:
Expected response:
Startup time estimate:
Docker health checks:

## Data Persistence
Application type:
External storage:
Docker volumes:
Database service:
Backup sidecar:
Backup provider:
Restore procedure:
Point-in-time restore supported:
Node migration persistence notes:
Known limitations:

## Local Verification Evidence
Commands run:
Results:
Known limitations:

## Deployment Notes for V-Decent Operator
Any special notes needed before approval/deployment.
```

---

## V-Decent Application Manager Flow to Support

Design the repository so the developer can follow this deployment flow:

1. Build and code the application according to V-Decent standards.
2. Verify locally using Docker Compose.
3. Obtain customer/application owner approval.
4. Register the application in V-Decent Application Manager at `https://am-dev.v-decent.org`.
5. Provide identity and ownership information:
   - Developer group
   - GitHub account or organization
6. Provide application details:
   - Application name
   - Primary shortname
   - Primary FQDN under `*.v-decent.org`
   - Category/resource size
7. Provide deployment source:
   - Git repository URL
   - Repository visibility
   - Branch
8. For public repositories:
   - Use HTTPS repository URL.
   - No deploy key setup should be required.
9. For private repositories:
   - Select **Private Repository**.
   - Copy the public key shown by V-Decent Application Manager.
   - Configure the Git provider/repository to allow access with that key.
   - Run or support **Analyze Manifest** so Application Manager can read `docker-compose.yaml`.
10. Ensure **Analyze Manifest** can detect the Compose services.
11. Select which service/container is exposed publicly.
12. Leave URL fields empty for internal-only services.
13. Provide production environment variables.
14. Register the application.
15. Trigger deployment by selecting **Deploy**.
16. Confirm final status becomes `HEALTHY`.
17. If deployment becomes `UNHEALTHY`, check system logs and fix the app, compose file, ingress network configuration, health check, backup sidecar, database, or environment variables.

---

## Public Repository Requirements

If the repository is public:

```text
Use HTTPS repository URL.
No deploy key setup should be required.
Provide repository URL, branch, and production environment variables.
Make sure docker-compose.yaml is present at repository root.
```

Avoid this mistake:

```text
Wrong or inaccessible repository URL format.
```

---

## Private Repository Requirements

If the repository is private:

```text
The V-Decent Application Manager must be authorized to access it.
The developer must associate the Application Manager login with the Git provider account when required.
The developer must copy the correct public key shown by Application Manager.
The developer must configure that public key in the Git provider or repository.
The developer must verify that Application Manager can analyze the manifest.
```

Avoid these mistakes:

```text
Private repository public key not configured.
Wrong public key copied.
Deploy key configured on the wrong repository or account.
Application Manager cannot access docker-compose.yaml.
Manifest file has the wrong name.
```

---

## URL and Domain Constraints

As of the V-Decent Application Development Guide V2.1, custom application domains are not supported by V-Decent Application Manager.

Use only:

```text
https://<shortname>.v-decent.org
```

Do not assume that a custom domain can be used unless the V-Decent Operator confirms support.

---

## Local Testing Requirements

Before handing the application to V-Decent operations, run and document:

```bash
docker compose config
docker compose build
docker compose up
docker compose ps
docker compose logs
```

Test the health endpoint:

```bash
curl -i http://localhost:<LOCAL_TEST_PORT>/health
```

Test the main application route:

```bash
curl -i http://localhost:<LOCAL_TEST_PORT>/
```

For apps with a database:

```bash
docker compose exec db pg_isready -U <USER> -d <DATABASE>
```

For apps with a backup sidecar, document the backup and restore verification commands, for example:

```bash
docker compose logs backup-sidecar
docker compose exec backup-sidecar <BACKUP_TEST_COMMAND>
docker compose exec backup-sidecar <RESTORE_DRY_RUN_COMMAND>
```

If a separate local override file is needed, create:

```text
docker-compose.local.yaml
```

Example local command:

```bash
docker compose -f docker-compose.yaml -f docker-compose.local.yaml up --build
```

The main `docker-compose.yaml` must remain V-Decent compatible and must not depend on host port mappings.

---

## AI Agent Development Instructions

When generating code, follow these rules:

1. Prefer simple, reliable architecture over unnecessary complexity.
2. Keep the application container stateless unless the selected pattern explicitly requires state.
3. Use environment variables for all deployment-specific values.
4. Do not hardcode production secrets.
5. Do not use host port mappings in the primary `docker-compose.yaml`.
6. Add a `/health` endpoint.
7. Add Docker health checks.
8. Add `.env.example`.
9. Add clear README instructions.
10. Add `docs/vdecent-handover.md`.
11. Use discrete Docker volumes for any persistent data.
12. Do not expose databases, workers, backup containers, or internal services publicly.
13. Connect only the public-facing web/API service to `vdecent-ingress`.
14. Keep databases, queues, workers, and backup sidecars on internal bridge networks.
15. Add `vdecent-ingress` as an external network in `docker-compose.yaml` for public-facing services.
16. Include `coolify.managed=true` label on the public-facing service unless the V-Decent Operator says otherwise.
17. Make startup ordering explicit with `depends_on` and health checks where needed.
18. Make logs useful for debugging deployment failures.
19. Ensure the app can restart cleanly with `restart: always`.
20. For stateful apps, document backup/restore behavior and limitations.

---

## Acceptance Criteria

The project is complete only when all items below are true:

```text
[ ] Root-level docker-compose.yaml exists.
[ ] docker-compose.yaml uses expose instead of ports for V-Decent-facing services.
[ ] Public-facing service joins external network vdecent-ingress.
[ ] Internal services do not join vdecent-ingress unless explicitly approved.
[ ] docker-compose.yaml defines vdecent-ingress as external: true with name: vdecent-ingress.
[ ] Public-facing service includes a Docker health check.
[ ] Application has a Dockerfile.
[ ] Application has .env.example.
[ ] Application has README.md with V-Decent deployment notes.
[ ] Application has docs/vdecent-handover.md.
[ ] Application provides /health endpoint.
[ ] Docker health checks are configured for database/internal services where applicable.
[ ] Public-facing service is clearly identified.
[ ] Internal services are not exposed publicly.
[ ] Production environment variables are documented.
[ ] Local Docker Compose startup has been tested.
[ ] Stateful data, if any, is stored in discrete Docker volumes or external storage.
[ ] Backup sidecar behavior is documented if internal stateful data is used.
[ ] Private repository instructions are included if repo visibility is private.
[ ] Deployment URL uses *.v-decent.org unless V-Decent Operator confirms otherwise.
[ ] Application Manager Analyze Manifest can detect docker-compose.yaml and services.
```

---

## Common Pitfalls to Avoid

Do not make these mistakes:

```text
Using ports in the primary docker-compose.yaml.
Naming the file something other than docker-compose.yaml.
Forgetting .env.example.
Forgetting Docker health checks.
Forgetting the /health endpoint.
Forgetting to attach the public web/API service to vdecent-ingress.
Attaching db, redis, worker, or backup-sidecar services to vdecent-ingress unnecessarily.
Forgetting to declare vdecent-ingress as external: true.
Exposing the database publicly.
Assuming container filesystem data will persist.
Assuming database data is guaranteed without backup.
Forgetting to document backup/restore for stateful apps.
Assuming custom domains are supported.
Using the wrong private repository public key.
Providing the wrong repository URL.
Failing to document production environment variables.
Skipping Analyze Manifest for private repository registration.
```

---

## Final Output Expected From the AI Agent

Produce:

```text
Complete application source code
Dockerfile
docker-compose.yaml
.env.example
README.md
docs/vdecent-handover.md
Any required database migration or initialization scripts
Any required backup sidecar scripts or documentation
Local test commands and expected results
Brief explanation of how to register/deploy in V-Decent Application Manager
```

Before finishing, inspect the generated project against the acceptance criteria and fix any missing item.
