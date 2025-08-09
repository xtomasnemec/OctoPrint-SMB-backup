# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin


import os
from smbprotocol.connection import Connection
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect
from smbprotocol.open import Open, CreateDisposition, FileAttributes

class SMBbackupPlugin(octoprint.plugin.SettingsPlugin,
					 octoprint.plugin.AssetPlugin,
					 octoprint.plugin.TemplatePlugin,
					 octoprint.plugin.EventHandlerPlugin,
					 octoprint.plugin.SimpleApiPlugin):

	##~~ SettingsPlugin mixin

	def __init__(self):
		super().__init__()

	def get_settings_defaults(self):
		return dict(
			installed_version=self._plugin_version,
			strip_timestamp=False,
			smb_server="",
			smb_share="",
			smb_username="",
			smb_password="",
			smb_path="",
			local_backup_path="",
			smb_backup_limit=0  # 0 = neomezeno
		)

	##~~ SimpleApiPlugin mixin

	def get_api_commands(self):
		return dict()

	def on_api_command(self, command, data):
		# API commands nejsou potřeba pro SMB
		pass

	##~~ AssetPlugin mixin

	def get_assets(self):
		# Define your plugin's asset files to automatically include in the
		# core UI here.
		return dict(
			js=["js/googledrivebackup.js"]
		)

	##~~ EventHandlerPlugin mixin

	def on_event(self, event, payload):
		if event == "plugin_backup_backup_created":
			self._logger.info("{} created, will now attempt to upload to SMB share and/or local path".format(payload["path"]))
			filename = payload["name"]
			if self._settings.get_boolean(["strip_timestamp"]):
				import re
				filename = re.sub(r"((-[0-9]+)+\.zip$)", ".zip", filename)
			# Lokální kopie
			local_backup_path = self._settings.get(["local_backup_path"])
			local_copy_path = None
			if local_backup_path:
				import shutil, os
				os.makedirs(local_backup_path, exist_ok=True)
				local_copy_path = os.path.join(local_backup_path, filename)
				shutil.copy2(payload["path"], local_copy_path)
			# SMB kopie
			try:
				server = self._settings.get(["smb_server"])
				share = self._settings.get(["smb_share"])
				username = self._settings.get(["smb_username"])
				password = self._settings.get(["smb_password"])
				smb_path = self._settings.get(["smb_path"])
				backup_limit = int(self._settings.get(["smb_backup_limit"]) or 0)
				if server and share and username and password and smb_path:
					conn = Connection(uuid=os.urandom(16), server=server, port=445)
					conn.connect()
					session = Session(conn, username, password)
					session.connect()
					tree = TreeConnect(session, f"//{server}/{share}")
					tree.connect()
					remote_path = smb_path.rstrip("/") + "/" + filename
					with open(payload["path"], "rb") as local_file:
						file = Open(tree, remote_path, access_mask=0x12019f, disposition=CreateDisposition.FILE_OVERWRITE_IF, attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL)
						file.create()
						file.write(local_file.read(), 0)
						file.close()
					# Smazání lokální kopie po úspěšném uploadu
					if local_copy_path:
						import os
						try:
							os.remove(local_copy_path)
						except Exception as e:
							self._logger.warning(f"Could not remove local backup: {e}")
					# Limit počtu záloh na SMB
					if backup_limit > 0:
						from smbprotocol.file_info import FileInformationClass
						from smbprotocol.open import Open
						from smbprotocol.query_directory import QueryDirectoryFlags
						dir_open = Open(tree, smb_path.rstrip("/"), access_mask=0x12019f)
						dir_open.create()
						files = dir_open.query_directory("*.zip", FileInformationClass.FILE_DIRECTORY_INFORMATION, flags=QueryDirectoryFlags.SL_RESTART_SCAN)
						# Seřadit podle času vytvoření (nejstarší první)
						files = sorted([f for f in files if not f['file_name'].startswith('.')], key=lambda x: x['creation_time'])
						if len(files) > backup_limit:
							for f in files[:-backup_limit]:
								try:
									old_file = Open(tree, smb_path.rstrip("/") + "/" + f['file_name'], access_mask=0x10000)
									old_file.create()
									old_file.delete()
									old_file.close()
								except Exception as e:
									self._logger.warning(f"Could not delete old backup {f['file_name']}: {e}")
						dir_open.close()
					tree.disconnect()
					session.disconnect()
					conn.disconnect()
			except Exception as e:
				self._plugin_manager.send_plugin_message(self._identifier, {"error": str(e)})

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
