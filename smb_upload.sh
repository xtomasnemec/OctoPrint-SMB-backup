#!/bin/bash

# server share user pass remote_path local_dir
SMB_SERVER="$1"
SMB_SHARE="$2"
SMB_USER="$3"
SMB_PASS="$4"
SMB_PATH="$5"
LOCAL_BACKUP_DIR="$6"

LOGFILE="/tmp/smb_backup_upload.log"
echo "=== SMB BACKUP UPLOAD $(date) ===" >> "$LOGFILE"

for file in "$LOCAL_BACKUP_DIR"/*.zip; do
  if [ -f "$file" ]; then
    echo "Uploading $file..." | tee -a "$LOGFILE"
    smbclient "//$SMB_SERVER/$SMB_SHARE" "$SMB_PASS" -U "$SMB_USER" -c "cd $SMB_PATH; put \"$file\"" >> "$LOGFILE" 2>&1
    if [ $? -eq 0 ]; then
      echo "OK: $file" | tee -a "$LOGFILE"
    else
      echo "ERROR: $file" | tee -a "$LOGFILE"
    fi
  fi
done

echo "Done." | tee -a "$LOGFILE"