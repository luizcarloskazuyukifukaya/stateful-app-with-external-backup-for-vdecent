# Stateful Activity Log with External Backup

## Overview
A stateful activity logging application built with Node.js and PostgreSQL. It features an automated backup sidecar that persists data to Google Drive, ensuring durability and point-in-time restore capabilities even in a distributed infrastructure.

## Technology Stack
- **Language/Framework:** Node.js, Express
- **Database:** PostgreSQL 16
- **Backup Sidecar:** Python 3 (custom script)
- **External Storage:** Google Drive (via Google Drive API)
- **Deployment Platform:** V-Decent (Docker Compose, Coolify)

## V-Decent Compatibility
This application is designed for **V-Decent** deployment (Guide V2.1).

- **Docker Compose file:** `docker-compose.yaml`
- **No host port mappings:** Uses `expose` instead of `ports` for internal/ingress routing.
- **Public-facing service:** `app`
- **Internal exposed port:** `80`
- **Ingress Network:** The `app` service joins the external `vdecent-ingress` network.
- **Isolation:** Internal services (`db`, `sidecar`) are isolated on an internal bridge network.
- **Health Checks:** Docker health checks are configured for `app` and `db`.
- **Health Endpoint:** Exposes `GET /health` on the `app` service.
- **Environment Variables:** Configured via `.env` with a provided `.env.example`.
- **Classification:** Pattern C — Stateful Application with Internal Data (Supported with External Backup Sidecar).
- **Backup Sidecar:** Included and automated to sync with Google Drive.

## Local Development

### 1. Copy Environment File
```bash
cp .env.example .env
```

### 2. Build and Start
For local development, we use an override file to map ports to your host machine:
```bash
docker compose -f docker-compose.yaml -f docker-compose.local.yaml up --build
```
Or use the provided convenience script:
```bash
chmod +x run_local.sh
./run_local.sh
```

### 3. Test Health
```bash
curl -i http://localhost:<LOCAL_PORT>/health
```

## Production Environment Variables
These variables must be supplied to the V-Decent Application Manager:

- `DATABASE_URL`: Connection string (e.g., `postgres://user:password@db:5432/activitylog`).
- `GOOGLE_DRIVE_FOLDER_ID`: The ID of the Google Drive folder for backups.
- `RESTORE_AUTH_TOKEN`: Secret token for authorizing restore/backup API calls.
- `GOOGLE_API_CREDENTIALS_B64`: Base64 encoded `credentials.json`.
- `GOOGLE_API_TOKEN_B64`: Base64 encoded `token.json`.
- `BACKUP_RETENTION_COUNT`: (Optional) Number of backups to keep (default: 5).
- `BACKUP_INTERVAL_MINS`: (Optional) Frequency of backups in minutes (default: 5).

## Deployment Source
- **Repository URL:** https://github.com/luizcarloskazuyukifukaya/stateful-app-with-external-backup-for-vdecent
- **Branch:** main (or docker-network-enhancement)
- **Repository visibility:** Public

## V-Decent Application Manager Registration Notes
- **Public-facing service:** `app`
- **Production URL:** `https://<shortname>.v-decent.org`
- **Internal services (Not exposed):** `db`, `sidecar`
- **Isolated from vdecent-ingress:** `db`, `sidecar`

## Data Persistence and Backup
- **Application type:** Pattern C (Stateful with Internal Data)
- **External storage:** Google Drive
- **Docker volumes:** `postgres_data`, `app_uploads`
- **Backup sidecar:** Python-based service running `pg_dump` (for the database) and archiving all other directories under `/backup/volumes/` into a consolidated `.tar.gz` archive (e.g. `backup_YYYYMMDD_HHMMSS.tar.gz`).
- **Backup target:** Google Drive folder.
- **Restore procedure:** Use the Sidecar API `/api/restore` with a valid `file_id` and auth token. It will unpack the archive, restore the filesystem volumes, and run the SQL database restoration.
- **Known limitations:** Backup interval minimum is 5 minutes. Initial restore on first deployment requires an existing backup in the specified Google Drive folder.

### What IS Backed Up:
- **Database Tables & Rows**: Exported via `pg_dump` as `db_backup.sql` inside the backup archive.
- **Application Docker Volumes**: Any filesystem directory declared as a named volume in `docker-compose.yaml` and mounted to the `sidecar` container under `/backup/volumes/` (e.g. `app_uploads` mounted at `/app/uploads`).

### What IS NOT Backed Up:
- **Application Source Code**: Managed, versioned, and backed up via GitHub repository.
- **Environment Variables & Secrets**: Managed separately by the PaaS / Host Environment (`.env`, `DATABASE_URL`, `RESTORE_AUTH_TOKEN`, `token.json`, etc.).
- **Unmounted Container Files**: Files stored directly inside the container's internal filesystem layer without a Docker volume mapping are ephemeral. The sidecar cannot access unmounted paths, and Docker will delete them upon container recreation.



## Troubleshooting
- **Startup:** Check logs via `docker compose logs -f`. Ensure `DATABASE_URL` matches the internal `db` service name.
- **Health Check:** If `app` is unhealthy, verify the database initialization in `server.js` succeeded.
- **Backup/Restore:** Ensure the Base64 encoded credentials/tokens are correctly set in the environment variables without line breaks.
- **Network:** Ensure the `vdecent-ingress` network exists on the host if running manually outside of a pre-configured V-Decent node.
