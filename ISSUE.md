  The Issue
  The sidecar was strictly filtering Google Drive files for the specific MIME type application/sql. When you upload a file
  manually through the Google Drive web interface, Google often automatically assigns it a different MIME type, such as
  text/plain or text/x-sql. Because of this mismatch, the sidecar was ignoring your manually copied files.
