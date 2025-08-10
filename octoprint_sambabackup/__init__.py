# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import os

class SMBbackupPlugin(octoprint.plugin.SettingsPlugin,
					 octoprint.plugin.AssetPlugin,
					 octoprint.plugin.TemplatePlugin,
					 octoprint.plugin.EventHandlerPlugin,
					 octoprint.plugin.SimpleApiPlugin,
					 octoprint.plugin.BlueprintPlugin):

	##~~ SettingsPlugin mixin

	def __init__(self):
		super().__init__()

	def get_settings_template(self):
		# Register the correct settings template for the plugin settings UI
		return "sambabackup_settings.jinja2"
	
	def get_template_configs(self):
		return [
			dict(type="settings", template="sambabackup_settings.jinja2")
		]

	def get_settings_defaults(self):
		return dict(
			installed_version=self._plugin_version,
			strip_timestamp=False,
			smb_server="",
			smb_share="",
			smb_username="",
			smb_password="",
			smb_path="",
			smb_backup_limit=0,  # 0 = neomezeno
			delete_local_after_smb=False
		)

	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict(test_connection=[], download_all_backups=[])

	def on_api_command(self, command, data):
		self._logger.info(f"[SMBbackup] API command received: {command}, data: {data}")
		if command == "test_connection":
			try:
				import subprocess
				import tempfile
				server = self._settings.get(["smb_server"])
				share = self._settings.get(["smb_share"])
				username = self._settings.get(["smb_username"])
				password = self._settings.get(["smb_password"])
				smb_path = self._settings.get(["smb_path"])
				if not (server and share and username and password and smb_path):
					self._logger.warning("[SMBbackup] Test connection failed: missing SMB fields.")
					return dict(result=False, error="Please fill in all SMB fields.")
				self._logger.info(f"[SMBbackup] Testing SMB connection to //{server}/{share}{smb_path} as {username}")
				
				# Testujeme připojení pomocí smbclient
				result = subprocess.run([
					"smbclient", f"//{server}/{share}", password, "-U", username, "-c", f"cd {smb_path}; quit"
				], capture_output=True, text=True)
				
				if result.returncode == 0:
					self._logger.info("[SMBbackup] Test connection successful.")
					return dict(result=True)
				else:
					self._logger.error(f"[SMBbackup] Test connection failed: {result.stderr}")
					return dict(result=False, error=result.stderr)
			except Exception as e:
				self._logger.error(f"[SMBbackup] Test connection failed: {e}")
				return dict(result=False, error=str(e))
		elif command == "download_all_backups":
			self._logger.info("[SMBbackup] API: Download all backups requested.")
			# Return a URL to download the zip file
			from flask import url_for
			return dict(result=True, url=url_for("plugin.sambabackup_download_all_backups"))
	##~~ Blueprint route for downloading all backups as zip
	def get_blueprint(self):
		from flask import Blueprint, send_file, make_response
		import io, zipfile
		blueprint = Blueprint(
			"sambabackup",
			__name__,
			template_folder="templates"
		)

		@blueprint.route("/download_all_backups.zip", methods=["GET"])
		def download_all_backups():
			self._logger.info("[SMBbackup] Blueprint: Download all backups endpoint called.")
			try:
				import subprocess
				import tempfile
				import os
				
				server = self._settings.get(["smb_server"])
				share = self._settings.get(["smb_share"])
				username = self._settings.get(["smb_username"])
				password = self._settings.get(["smb_password"])
				smb_path = self._settings.get(["smb_path"])
				if not (server and share and username and password and smb_path):
					self._logger.warning("[SMBbackup] Download all backups: SMB settings incomplete.")
					return make_response("SMB settings incomplete", 400)
				
				# Vytvoření dočasného adresáře pro stažené soubory
				temp_dir = tempfile.mkdtemp()
				self._logger.info(f"[SMBbackup] Dočasný adresář pro download: {temp_dir}")
				
				# Spuštění download skriptu
				script_path = "/home/pi/smb_download.sh"
				args = ["/bin/bash", script_path, server, share, username, password, smb_path, temp_dir]
				result = subprocess.run(args, capture_output=True, text=True)
				
				self._logger.info(f"[SMBbackup] Download skript stdout: {result.stdout}")
				if result.stderr:
					self._logger.warning(f"[SMBbackup] Download skript stderr: {result.stderr}")
				
				if result.returncode != 0:
					self._logger.error(f"[SMBbackup] Download skript selhal s kódem {result.returncode}")
					return make_response("Download script failed", 500)
				
				# Vytvoření ZIP z stažených souborů
				import zipfile
				import io
				mem_zip = io.BytesIO()
				with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
					for filename in os.listdir(temp_dir):
						if filename.endswith('.zip'):
							file_path = os.path.join(temp_dir, filename)
							zf.write(file_path, filename)
				
				# Smazání dočasného adresáře
				import shutil
				shutil.rmtree(temp_dir)
				
				mem_zip.seek(0)
				self._logger.info("[SMBbackup] Vytvoření ZIP archivu dokončeno.")
				return send_file(mem_zip, mimetype="application/zip", as_attachment=True, download_name="smb_backups.zip")
			except Exception as e:
				self._logger.error(f"[SMBbackup] Download all backups failed: {e}")
				return make_response(f"Failed to download backups: {e}", 500)
		
		return blueprint

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Plugin nemá žádné JS assety
		return dict()

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		self._logger.info(f"[SMBbackup] Event received: {event}, payload: {payload}")
		if event == "plugin_backup_backup_created":
			try:
				self._logger.info(f"[SMBbackup] Backup created: {payload['path']}, name: {payload['name']}")
				filename = payload["name"]
				if self._settings.get_boolean(["strip_timestamp"]):
					import re
					filename = re.sub(r"((-[0-9]+)+\.zip$)", ".zip", filename)
					self._logger.info(f"[SMBbackup] Stripped timestamp, new filename: {filename}")
				# Lokální kopie
				local_backup_path = "/home/pi/.octoprint/data/backup/"
				local_copy_path = os.path.join(local_backup_path, filename)
				import os, shutil
				if os.path.abspath(payload["path"]) != os.path.abspath(local_copy_path):
					os.makedirs(local_backup_path, exist_ok=True)
					shutil.copy2(payload["path"], local_copy_path)
					self._logger.info(f"[SMBbackup] Local backup copied to: {local_copy_path}")
				else:
					self._logger.info(f"[SMBbackup] Local backup already in destination: {local_copy_path}")
				# SMB upload přes shell skript
				import subprocess
				server = self._settings.get(["smb_server"])
				share = self._settings.get(["smb_share"])
				username = self._settings.get(["smb_username"])
				password = self._settings.get(["smb_password"])
				smb_path = self._settings.get(["smb_path"])
				local_backup_dir = "/home/pi/.octoprint/data/backup"  # nebo použijte proměnnou pokud je nastavitelná
				
				# Volba skriptu podle nastavení delete_local_after_smb
				if self._settings.get_boolean(["delete_local_after_smb"]):
					script_path = "/home/pi/smb_upload_delete.sh"
					self._logger.info(f"[SMBbackup] Použití skriptu s automatickým mazáním: {script_path}")
				else:
					script_path = "/home/pi/smb_upload.sh"
					self._logger.info(f"[SMBbackup] Použití běžného upload skriptu: {script_path}")
				
				try:
					self._logger.info(f"[SMBbackup] Spouštím upload přes shell skript: {script_path}")
					args = ["/bin/bash", script_path, server, share, username, password, smb_path, local_backup_dir]
					result = subprocess.run(args, capture_output=True, text=True)
					self._logger.info(f"[SMBbackup] SMB upload skript stdout: {result.stdout}")
					if result.stderr:
						self._logger.warning(f"[SMBbackup] SMB upload skript stderr: {result.stderr}")
					if result.returncode == 0:
						self._logger.info(f"[SMBbackup] SMB upload skript dokončen úspěšně.")
						# Pokud nepoužíváme delete skript, můžeme smazat lokální kopii zde
						if not self._settings.get_boolean(["delete_local_after_smb"]) and self._settings.get_boolean(["delete_local_after_smb"]):
							# Tato logika je redundantní, protože delete skript to už udělá
							pass
					else:
						self._logger.error(f"[SMBbackup] SMB upload skript selhal s kódem {result.returncode}")
				except Exception as e:
					self._logger.error(f"[SMBbackup] Chyba při spouštění SMB upload skriptu: {e}")
			except Exception as e:
				self._logger.error(f"[SMBbackup] Backup event handling failed: {e}")

	# Funkce create_remote_folder již není potřeba

	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			smbbackup=dict(
				displayName="SMB Backup",
				displayVersion=self._plugin_version,
				type="github_release",
				user="xtomasnemec",
				repo="OctoPrint-SMB-backup",
				current=self._plugin_version,
				stable_branch=dict(
					name="Stable",
					branch="master",
					comittish=["master"]
				),
				prerelease_branches=[
					dict(
						name="Release Candidate",
						branch="rc",
						comittish=["rc", "master"]
					)
				],
				pip="https://github.com/xtomasnemec/OctoPrint-SMB-backup/archive/{target_version}.zip"
			)
		)


__plugin_name__ = "SMB Backup"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = SMBbackupPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
