# OctoPrint SMB Backup

This plugin automatically saves your OctoPrint backups to an SMB (Samba/CIFS) network share and/or a local folder on your Raspberry Pi.

## Features

- Automatically uploads backups to an SMB share after creation
- Optionally saves a copy to a local folder on the Raspberry Pi
- Local copy is deleted after successful upload to SMB
- Configurable backup limit on the SMB share (oldest backups are deleted automatically)

## Installation

1. Open OctoPrint's web interface.
2. Go to **Settings → Plugin Manager → Get More...**
3. At the bottom, paste this URL into the "...from URL" field:

    ```
    https://github.com/xtomasnemec/OctoPrint-SMB-backup/archive/master.zip
    ```

4. Click "Install" and restart OctoPrint when prompted.

You will find the plugin in OctoPrint's settings under "SMB Backup".

## Requirements

- Python package `smbprotocol` (installed automatically)
- OctoPrint 1.5.0 or newer

## Configuration

In the plugin settings, fill in:

- **SMB server** – IP address or hostname of the server
- **SMB share** – name of the shared folder
- **SMB username** and **password** – login credentials
- **SMB path** – path within the share (e.g. `/octoprint`)
- **Local backup path** – local folder on the Raspberry Pi (optional)
- **SMB backup limit** – maximum number of backups to keep on the SMB share (0 = unlimited)

## How it works

1. When a backup is created in OctoPrint, the file is copied to the SMB share and/or the local folder.
2. If the upload to SMB is successful, the local copy is deleted.
3. If there are more backups on the SMB share than the set limit, the oldest backups are deleted automatically.

## Uninstallation

You can uninstall the plugin via the Plugin Manager or with:

```sh
~/oprint/bin/pip uninstall octoprint-sambabackup
```

## Support

If you encounter any issues, please open an issue on [GitHub](https://github.com/xtomasnemec/OctoPrint-SMB-backup).

## Configuration
Once the Prerequisite steps above have been completed and you have downloaded your client_secrets.json file follow these steps to authorize the plugin to your newly created app.

## Get Help

If you experience issues with this plugin or need assistance please use the issue tracker by clicking issues above.