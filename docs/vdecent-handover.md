# V-Decent Deployment Handover

## Application Identity
- **Application name:** Stateful Activity Log
- **Primary shortname:** activity-log
- **Production URL:** https://activity-log.v-decent.org
- **Developer group:** V-Decent Team
- **GitHub account or organization:** luizcarloskazuyukifukaya

## Deployment Source
- **Repository URL:** https://github.com/luizcarloskazuyukifukaya/stateful-app-with-external-backup-for-vdecent
- **Repository visibility:** Public
- **Branch:** docker-network-enhancement
- **Manifest file:** docker-compose.yaml

## Service Exposure
| Service | Expose Publicly? | URL | Networks | Notes |
|---|---:|---|---|---|
| app | Yes | https://activity-log.v-decent.org | app-network, vdecent-ingress | Main web/API service |
| db | No | | app-network | Internal database only |
| sidecar | No | | app-network | Internal backup service |

## Environment Variables for Production
```env
# Required for App
DATABASE_URL=postgres://user:password@db:5432/activitylog

# Required for Backup Sidecar
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
RESTORE_AUTH_TOKEN=your_secure_token
GOOGLE_API_CREDENTIALS_B64=base64_encoded_json
GOOGLE_API_TOKEN_B64=base64_encoded_json

# Optional
BACKUP_RETENTION_COUNT=5
BACKUP_INTERVAL_MINS=5
```

## Health Check
- **Health endpoint:** `/health`
- **Expected response:** `{"status":"UP", ...}` (HTTP 200)
- **Startup time estimate:** ~10-20 seconds
- **Docker health checks:** 
  - `app`: `wget -qO- http://localhost:80/health`
  - `db`: `pg_isready -U user -d activitylog`

## Data Persistence
- **Application type:** Pattern C (Stateful with Internal Data)
- **External storage:** Google Drive
- **Docker volumes:** `postgres_data`
- **Database service:** `db` (Postgres 16)
- **Backup sidecar:** `sidecar` (Python)
- **Backup provider:** Google Drive API
- **Restore procedure:** Trigger `POST /api/restore` on the `sidecar` service with a `file_id`.
- **Point-in-time restore supported:** Yes (manual selection of backup file).
- **Node migration persistence notes:** Data is backed up to Google Drive and automatically restored on fresh deployment if the database is empty.
- **Known limitations:** Backup granularity is limited to the configured interval (min 5 mins).

## Local Verification Evidence
- **Commands run:**
  ```bash
  docker compose config
  docker compose build
  docker compose up -d
  docker compose ps
  curl -i http://localhost:80/health
  ```
- **Results:** Application starts correctly, database initializes, and health endpoint returns 200 OK.
- **Known limitations:** Local testing requires pre-existing `vdecent-ingress` network or use of `docker-compose.local.yaml`.

## Deployment Notes for V-Decent Operator
- The application automatically attempts to restore the latest backup from Google Drive if it detects an empty database on startup.
- Ensure the `GOOGLE_API_*_B64` variables are provided as single-line strings.
