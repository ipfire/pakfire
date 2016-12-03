#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import configparser
import io
import logging
import os
import socket

log = logging.getLogger("pakfire.config")
log.propagate = 1

from .system import system

from .constants import *
from .i18n import _

class Config(object):
	def __init__(self, *files):
		self._config = configparser.ConfigParser(
			interpolation=configparser.ExtendedInterpolation()
		)

		# Read any passed configuration files
		for f in files:
			self.read(f)

	def read(self, path):
		"""
			Reads configuration from the given file
		"""
		if not path.startswith("/"):
			path = os.path.join(CONFIG_DIR, path)

		log.debug("Reading configuration from %s" % path)

		with open(path) as f:
			self._config.read_file(f)

	def parse(self, s):
		"""
			Takes configuration as a string and parses it
		"""
		self._config.read_string(s)

	def get(self, section, option=None, default=None):
		if option is None:
			try:
				section = self._config.items(section)
			except configparser.NoSectionError:
				return default

			return dict(section)

		return self._config.get(section, option, fallback=default)

	def get_bool(self, section, option, default=None):
		return self._config.getboolean(section, option, fallback=default)

	def dump(self):
		"""
			Dump the configuration that was read

			(Only in debugging mode)
		"""
		log.debug(_("Configuration:"))

		for section in self._config.sections():
			log.debug("  " + _("Section: %s") % section)

			for option in self._config[section]:
				value = self.get(section, option)

				log.debug("    %-20s: %s" % (option, value))

	def get_repos(self):
		repos = []
		for section in self._config.sections():
			if not section.startswith("repo:"):
				continue

			name = section[5:]

			repo = self._config.items(section)
			repos.append((name, dict(repo)))

		return repos


# Read initial configuration
config = Config("general.conf")

class _Config(object):
	files = []

	global_default_settings = {
		"logger" : {
			"file"  : "/var/log/pakfire.log",
			"level" : "normal",
			"mode"  : "rotate",
			"rotation_threshold" : 10485760,
		},

		"signatures" : {
			"mode" : "strict",
		},
	}

	# A dict with default settings for this config class.
	default_settings = {}

	def __init__(self, files=None):
		# Configuration settings.
		self._config = self.global_default_settings.copy()
		self._config.update(self.default_settings)

		# List of files that were already loaded.
		self._files = []

		# If no files were given, load the default files.
		if files is None:
			# Read default configuration file.
			self.read(*self.files)

			repo_path = self.get(None, "repo_path", CONFIG_REPOS_DIR)
			if repo_path:
				self.read_dir(repo_path, ext=".repo")

		# Always read overwrite.conf.
		# This is a undocumented feature to make bootstrapping easier.
		self.read("overwrite.conf")

	def get_repos(self):
		repos = []

		for name, settings in list(self._config.items()):
			if not name.startswith("repo:"):
				continue

			# Strip "repo:" from name of the repository.
			name = name[5:]

			repos.append((name, settings))

		return repos

	def read_dir(self, where, ext=".conf"):
		for file in os.listdir(where):
			if not file.endswith(ext):
				continue

			file = os.path.join(where, file)
			self.read(file)

	def read(self, *files):
		# Do nothing for no files.
		if not files:
			return

		for file in files:
			if not file.startswith("/"):
				file = os.path.join(CONFIG_DIR, file)

			if not os.path.exists(file):
				continue

			# Normalize filename.
			file = os.path.abspath(file)

			# Check if file has already been read or
			# does not exist. Then skip it.
			if file in self._files or not os.path.exists(file):
				continue

			# Parse the file.
			with open(file) as f:
				self.parse(f)

			# Save the filename to the list of read files.
			self._files.append(file)

	def parse(self, f):
		config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
		config.readfp(f)

		# Read all data from the configuration file in the _config dict.
		for section in config.sections():
			items = dict(config.items(section))

			if section == "DEFAULT":
				section = "main"

			try:
				self._config[section].update(items)
			except KeyError:
				self._config[section] = items

	def set(self, section, key, value):
		try:
			self._config[section][key] = value
		except KeyError:
			self._config[section] = { key : value }

	def get_section(self, section):
		try:
			return self._config[section]
		except KeyError:
			return {}

	def get(self, section, key, default=None):
		s = self.get_section(section)

		try:
			return s[key]
		except KeyError:
			return default

	def get_int(self, section, key, default=None):
		val = self.get(section=section, key=key, default=default)
		try:
			val = int(val)
		except ValueError:
			return default

	def get_bool(self, section, key, default=None):
		val = self.get(section=section, key=key, default=default)

		if val in (True, "true", "1", "on"):
			return True
		elif val in (False, "false", "0", "off"):
			return False

		return default

	def update(self, section, what):
		if not type(what) == type({}):
			log.error(_("Unhandled configuration update: %s = %s") % (section, what))
			return

		try:
			self._config[section].update(what)
		except KeyError:
			self._config[section] = what

	def dump(self):
		"""
			Dump the configuration that was read.

			(Only in debugging mode.)
		"""
		log.debug(_("Configuration:"))
		for section, settings in list(self._config.items()):
			log.debug("  " + _("Section: %s") % section)

			for k, v in list(settings.items()):
				log.debug("    %-20s: %s" % (k, v))
			else:
				log.debug("    " + _("No settings in this section."))

		log.debug("  " + _("Loaded from files:"))
		for f in self._files:
			log.debug("    %s" % f)

	def has_distro_conf(self):
		return "distro" in self._config

	def get_distro_conf(self):
		return self.get_section("distro")


class ConfigBuilder(_Config):
	files = ["general.conf", "builder.conf"]

	def load_distro_config(self, distro_name):
		if distro_name is None:
			return False

		filename = os.path.join(CONFIG_DISTRO_DIR, "%s.conf" % distro_name)

		if not os.path.exists(filename):
			return False

		self.read(filename)
		return True
