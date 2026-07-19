import os
import datetime
import subprocess
import logging
import base64
import tarfile
import shutil
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_gdrive_service():
    creds = None
    token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    
    # Handle Base64 encoded credentials and tokens from environment variables
    creds_b64 = os.getenv('GOOGLE_API_CREDENTIALS_B64')
    token_b64 = os.getenv('GOOGLE_API_TOKEN_B64')

    if creds_b64:
        logger.info(f"GOOGLE_API_CREDENTIALS_B64 detected. Writing to {creds_path}...")
        try:
            creds_json = base64.b64decode(creds_b64).decode('utf-8')
            with open(creds_path, 'w') as f:
                f.write(creds_json)
        except Exception as e:
            logger.error(f"Failed to decode GOOGLE_API_CREDENTIALS_B64: {e}")

    if token_b64:
        logger.info(f"GOOGLE_API_TOKEN_B64 detected. Writing to {token_path}...")
        try:
            token_json = base64.b64decode(token_b64).decode('utf-8')
            with open(token_path, 'w') as f:
                f.write(token_json)
        except Exception as e:
            logger.error(f"Failed to decode GOOGLE_API_TOKEN_B64: {e}")

    if os.path.exists(token_path) and os.path.getsize(token_path) > 0:
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.warning(f"Could not load token from {token_path}: {e}")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(f"Credentials file not found at {creds_path}")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def perform_backup():
    logger.info("Starting database and volume backup...")
    try:
        # Get environment variables
        db_url = os.getenv('DATABASE_URL')
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        if not db_url:
            raise ValueError("DATABASE_URL is not set")

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        db_sql_file = "db_backup.sql"
        archive_file = f"backup_{timestamp}.tar.gz"

        # 1. Run pg_dump to create a logical database backup
        logger.info("Dumping database to sql...")
        result = subprocess.run(['pg_dump', db_url, '--clean', '--if-exists', '-f', db_sql_file], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"pg_dump failed: {result.stderr}")
            return False, result.stderr

        # Workaround for version mismatch: remove SET transaction_timeout = 0; if present
        if os.path.exists(db_sql_file):
            with open(db_sql_file, 'r') as f:
                lines = f.readlines()
            with open(db_sql_file, 'w') as f:
                for line in lines:
                    if "SET transaction_timeout = 0;" not in line:
                        f.write(line)

        # 2. Package the SQL dump and non-db volumes into a compressed tarball
        logger.info("Creating consolidated tarball archive...")
        with tarfile.open(archive_file, "w:gz") as tar:
            # Add database backup at root
            if os.path.exists(db_sql_file):
                logger.info("Adding database SQL dump to archive: db_backup.sql")
                tar.add(db_sql_file, arcname="db_backup.sql")
            
            # Add filesystem volumes under volumes/
            volumes_dir = "/backup/volumes"
            if os.path.exists(volumes_dir):
                for item in os.listdir(volumes_dir):
                    item_path = os.path.join(volumes_dir, item)
                    if os.path.isdir(item_path) and item != "postgres_data":
                        logger.info(f"Adding volume directory: {item}")
                        
                        def log_filter(tarinfo):
                            if tarinfo.isfile():
                                logger.info(f"  -> Archiving file: {tarinfo.name} ({tarinfo.size} bytes)")
                            elif tarinfo.isdir():
                                logger.info(f"  -> Archiving directory: {tarinfo.name}")
                            return tarinfo
                        
                        tar.add(item_path, arcname=os.path.join("volumes", item), filter=log_filter)


        # 3. Upload to Google Drive
        service = get_gdrive_service()
        file_metadata = {'name': archive_file}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(archive_file, mimetype='application/gzip')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        logger.info(f"Archive backup uploaded successfully. File ID: {file.get('id')}")
        
        # Clean up local temporary files
        if os.path.exists(db_sql_file):
            os.remove(db_sql_file)
        if os.path.exists(archive_file):
            os.remove(archive_file)

        # Automatically purge if retention is set
        perform_purge()
        
        return True, file.get('id')

    except Exception as e:
        logger.exception("An error occurred during backup")
        # Clean up any leftover local files in case of error
        if os.path.exists("db_backup.sql"):
            os.remove("db_backup.sql")
        if 'archive_file' in locals() and os.path.exists(archive_file):
            os.remove(archive_file)
        return False, str(e)


def perform_purge():
    logger.info("Checking for old backups to purge...")
    try:
        retention_count_str = os.getenv('BACKUP_RETENTION_COUNT')
        if not retention_count_str:
            logger.info("BACKUP_RETENTION_COUNT not set. Skipping purge.")
            return True, "No retention set"
        
        retention_count = int(retention_count_str)
        success, result = list_backups()
        if not success:
            return False, result
        
        files = result
        logger.info(f"Found {len(files)} backups.")

        if len(files) > retention_count:
            files_to_delete = files[retention_count:]
            logger.info(f"Purging {len(files_to_delete)} old backups...")
            service = get_gdrive_service()
            for f in files_to_delete:
                logger.info(f"Deleting old backup: {f['name']} (ID: {f['id']})")
                service.files().delete(fileId=f['id']).execute()
            return True, f"Purged {len(files_to_delete)} files"
        
        return True, "No files to purge"

    except Exception as e:
        logger.exception("An error occurred during purge")
        return False, str(e)

def list_backups():
    logger.info("Listing backups from Google Drive...")
    try:
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        service = get_gdrive_service()
        
        # Be inclusive of both new .tar.gz volume archives and legacy .sql backups
        query = "(mimeType = 'application/gzip' or mimeType = 'application/x-gzip' or mimeType = 'application/x-tar' or mimeType = 'application/sql' or name contains '.tar.gz' or name contains '.sql') and trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime, size, mimeType)',
            orderBy='createdTime desc'
        ).execute()
        
        files = results.get('files', [])
        
        # Filter for files that have tar.gz/sql extensions or corresponding mime types
        backups = [
            f for f in files 
            if f['name'].lower().endswith('.tar.gz') 
            or f['name'].lower().endswith('.sql') 
            or f.get('mimeType') in ['application/gzip', 'application/x-gzip', 'application/x-tar', 'application/sql']
        ]
        
        return True, backups
    except Exception as e:
        logger.exception("An error occurred while listing backups")
        return False, str(e)


import time
import psycopg2
from urllib.parse import urlparse

def wait_for_db(timeout=60):
    logger.info("Waiting for database to be ready...")
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL is not set.")
        return False
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            logger.info("Database is ready.")
            return True
        except Exception:
            time.sleep(2)
    
    logger.error(f"Database wait timed out after {timeout} seconds.")
    return False

def is_db_empty():
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if there are any tables in the public schema
        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count = cur.fetchone()[0]
        
        if table_count == 0:
            conn.close()
            return True
            
        # If there are tables, check if all of them are empty (optional, but safer)
        # For now, if there are any tables, we check if the 'activities' table specifically has data
        # since that's our main data table. Or we can just say if there are tables, it's not empty.
        # Given the requirements, if it's the "first deployment", there should be NO tables.
        # But server.js might have created them.
        
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'activities')")
        if cur.fetchone()[0]:
            cur.execute("SELECT count(*) FROM activities")
            row_count = cur.fetchone()[0]
            conn.close()
            return row_count == 0
        
        conn.close()
        return False # Has other tables but not activities? Not empty.
    except Exception as e:
        logger.warning(f"Could not check if DB is empty: {e}. Assuming it might need restore.")
        return True

def restore_latest_on_startup():
    logger.info("Checking if initial restore is needed...")
    if not wait_for_db():
        return
    
    if not is_db_empty():
        logger.info("Database is not empty. Skipping initial restore.")
        return

    logger.info("Database is empty. Attempting to restore latest backup from Google Drive...")
    success, backups = list_backups()
    if success and backups:
        latest_backup = backups[0]
        logger.info(f"Found latest backup: {latest_backup['name']} (ID: {latest_backup['id']})")
        perform_restore(latest_backup['id'])
    else:
        logger.info("No backups found in Google Drive to restore.")

def perform_restore(file_id):
    logger.info(f"Starting restore from file ID: {file_id}...")
    try:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL is not set")

        service = get_gdrive_service()
        
        # Get metadata to determine the format (.tar.gz or .sql)
        metadata = service.files().get(fileId=file_id, fields='name,mimeType').execute()
        filename = metadata.get('name', '')
        logger.info(f"Target backup filename: {filename}")

        is_tarball = filename.lower().endswith('.tar.gz') or 'gzip' in metadata.get('mimeType', '').lower()

        if is_tarball:
            # 1. Download tar.gz from Google Drive
            restore_archive = "restore_temp.tar.gz"
            logger.info(f"Downloading volume archive {filename}...")
            request = service.files().get_media(fileId=file_id)
            with open(restore_archive, "wb") as f:
                f.write(request.execute())

            # 2. Extract archive
            temp_extract_dir = "restore_temp_dir"
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir, exist_ok=True)
            
            logger.info("Extracting consolidated volume archive...")
            with tarfile.open(restore_archive, "r:gz") as tar:
                tar.extractall(path=temp_extract_dir)

            # 3. Restore filesystem volumes if they exist
            extracted_volumes_dir = os.path.join(temp_extract_dir, "volumes")
            if os.path.exists(extracted_volumes_dir):
                for volume_name in os.listdir(extracted_volumes_dir):
                    source_dir = os.path.join(extracted_volumes_dir, volume_name)
                    target_dir = os.path.join("/backup/volumes", volume_name)
                    
                    if os.path.isdir(source_dir):
                        logger.info(f"Restoring filesystem volume: {volume_name} to {target_dir}...")
                        if os.path.exists(target_dir):
                            # Clean out existing directory contents to ensure correct state
                            for entry in os.listdir(target_dir):
                                entry_path = os.path.join(target_dir, entry)
                                try:
                                    if os.path.isdir(entry_path):
                                        shutil.rmtree(entry_path)
                                    else:
                                        os.remove(entry_path)
                                except Exception as e:
                                    logger.warning(f"Failed to delete {entry_path} during restore cleanup: {e}")
                        else:
                            os.makedirs(target_dir, exist_ok=True)

                        # Copy extracted files to volume
                        for entry in os.listdir(source_dir):
                            src_path = os.path.join(source_dir, entry)
                            dst_path = os.path.join(target_dir, entry)
                            if os.path.isdir(src_path):
                                shutil.copytree(src_path, dst_path)
                            else:
                                shutil.copy2(src_path, dst_path)
            
            # 4. Restore database if SQL dump exists in archive
            db_sql_file = os.path.join(temp_extract_dir, "db_backup.sql")
            if os.path.exists(db_sql_file):
                logger.info("Database SQL dump found in archive. Starting database restore...")
                success, msg = _restore_db_from_sql_file(db_url, db_sql_file)
                if not success:
                    return False, f"Volume files restored but database restore failed: {msg}"
            else:
                logger.warning("No db_backup.sql found in archive. Skipping database restore.")

            # Clean up temp files
            if os.path.exists(restore_archive):
                os.remove(restore_archive)
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

            return True, "Volume and database restore successful"

        else:
            # Legacy/fallback behavior: direct SQL restore
            restore_file = "restore_temp.sql"
            logger.info(f"Downloading legacy SQL backup {filename}...")
            request = service.files().get_media(fileId=file_id)
            with open(restore_file, "wb") as f:
                f.write(request.execute())

            success, msg = _restore_db_from_sql_file(db_url, restore_file)
            
            if os.path.exists(restore_file):
                os.remove(restore_file)
                
            if success:
                return True, "Legacy SQL restore successful"
            else:
                return False, msg

    except Exception as e:
        logger.exception("An error occurred during restore")
        return False, str(e)

def _restore_db_from_sql_file(db_url, sql_file_path):
    try:
        # Pre-process the restore file for version compatibility
        if os.path.exists(sql_file_path):
            with open(sql_file_path, 'r') as f:
                content = f.read()
            
            # Remove transaction_timeout which is incompatible with Postgres < 17
            if "SET transaction_timeout = 0;" in content:
                logger.info("Removing 'SET transaction_timeout = 0;' for compatibility")
                content = content.replace("SET transaction_timeout = 0;", "-- SET transaction_timeout = 0; (removed for compatibility)")
            
            with open(sql_file_path, 'w') as f:
                f.write(content)

        # Clear the database before restore to handle old backups without --clean
        logger.info("Clearing public schema before restore to ensure a clean slate...")
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public; GRANT ALL ON SCHEMA public TO \"user\";")
            conn.close()
            logger.info("Public schema cleared successfully.")
        except Exception as e:
            logger.error(f"Failed to clear schema: {e}. Attempting restore anyway...")

        # Run psql to restore
        result = subprocess.run(['psql', '-v', 'ON_ERROR_STOP=1', db_url, '-f', sql_file_path], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"psql restore failed: {result.stderr}")
            return False, result.stderr

        logger.info("Database restore from SQL completed successfully.")
        return True, "Success"
    except Exception as e:
        logger.exception("Failed to restore db from SQL file")
        return False, str(e)

