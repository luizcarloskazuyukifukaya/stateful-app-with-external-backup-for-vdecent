# Development Plan: Stateful App with External DB Backup

This plan outlines the implementation of a sidecar container for automatic database backup and restore to Google Drive.

## Phase 1: Environment & Credentials Setup
- [x] Research Google Drive API requirements for Python/Node.js (matching existing `credentials.json` pattern).
- [x] Define required environment variables in `.env.example`:
    - `BACKUP_INTERVAL_MINS` (default: 5)
    - `GOOGLE_DRIVE_FOLDER_ID`
    - `RESTORE_AUTH_TOKEN` (for securing `/api/restore`)
    - Google API credentials path or inline JSON.

## Phase 2: Implement Backup Sidecar (Python)
- [x] Create `sidecar/` directory.
- [x] Implement `backup.py`:
    - Logic to run `pg_dump` on the `db` service.
    - Logic to upload dump files to Google Drive.
    - Scheduler to run backup every `BACKUP_INTERVAL_MINS`.
- [x] Implement `sidecar_api.py` (FastAPI or Flask):
    - `POST /api/backup`: Manually trigger backup.
    - `POST /api/restore`: Secure endpoint to restore from a specific Google Drive file.
- [x] Create `sidecar/Dockerfile`.

## Phase 3: Docker Integration
- [x] Update `docker-compose.yaml` to include the `sidecar` service.
- [x] Ensure `sidecar` has access to the database network and volumes if necessary.
- [x] Map sidecar API port if external access is needed, or keep it internal to the Docker network.

## Phase 4: Verification & Testing
- [x] Verify automatic backup occurs every 5 minutes (Logic implemented with min 5 check).
- [x] Test manual backup via API.
- [x] Test secure restore via API (validating auth token).
- [x] Verify persistence after restore.

## Phase 5: Documentation
- [x] Update `README.md` with instructions on how to configure Google Drive and use the backup/restore API.

## Phase 6: Purge Function Implementation
- [x] Update `.env.example` with `BACKUP_RETENTION_COUNT`.
- [x] Implement `perform_purge` in `backup.py`:
    - Logic to list files in Google Drive folder.
    - Logic to delete oldest files if count exceeds `BACKUP_RETENTION_COUNT`.
- [x] Update `sidecar_api.py` (main.py):
    - `POST /api/purge`: Secure endpoint to manually trigger purge.
    - Integration: Call `perform_purge` automatically after a successful `perform_backup`.
- [x] Verify purge logic works (automatic and manual).

## Phase 7: Initial Restore on Startup
- [x] Implement `wait_for_db` logic to ensure PostgreSQL is ready.
- [x] Implement `restore_latest_on_startup` logic:
    - [x] On sidecar start, check if the database is empty or if it's the first run.
    - [x] Fetch the latest backup ID from Google Drive using the `list_backups` logic.
    - [x] Perform restore if a backup exists.
- [x] Update `main.py` startup event to trigger the initial restore.
- [x] Verify that initial restore correctly populates the database on fresh deployment.

## Phase 8: Robustness & Compatibility
- [x] Add `--clean` and `--if-exists` to `pg_dump` for more reliable restores.
- [x] Implement pre-processing of SQL dumps to handle version mismatches (e.g., removing `transaction_timeout`).
- [x] Improve `is_db_empty` logic to be more generic across different schemas.
- [x] Fix MIME type filtering in Google Drive queries to be more inclusive of manually uploaded files.
- [ ] Add more comprehensive error handling and logging for Google Drive API interactions.

## Phase 9: Git Operations
- [x] Switch to `main` branch and verify its status.
- [x] Merge `docker-network-enhancement` into `main` and resolve any conflicts.
- [x] Verify both branches are fully synced and clean.
- [x] Delete `docker-network-enhancement` branch locally and remotely.


