#!/bin/bash

# server share user pass remote_path local_dir
SMB_SERVER="$1"
SMB_SHARE="$2"
SMB_USER="$3"
SMB_PASS="$4"
SMB_PATH="$5"
LOCAL_DIR="$6"

LOGFILE="/tmp/smb_backup_download.log"
echo "=== SMB BACKUP DOWNLOAD $(date) ===" >> "$LOGFILE"

mkdir -p "$LOCAL_DIR"

SMB_CMDS=$(mktemp)
echo "cd $SMB_PATH" > "$SMB_CMDS"
echo "mget *" >> "$SMB_CMDS"
echo "quit" >> "$SMB_CMDS"

smbclient "//$SMB_SERVER/$SMB_SHARE" "$SMB_PASS" -U "$SMB_USER" -D "$SMB_PATH" -c "prompt OFF; recurse ON; mget *" -d 1 -W WORKGROUP -m SMB3 -I "$SMB_SERVER" -Tc "$SMB_CMDS" -D "$LOCAL_DIR" >> "$LOGFILE" 2>&1

if [ $? -eq 0 ]; then
  echo "Download completed successfully." | tee -a "$LOGFILE"
else
  echo "Error during download!" | tee -a "$LOGFILE"
fi

rm -f "$SMB_CMDS"