#!/usr/bin/python
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

import os

from ConfigParser import ConfigParser

import logging
log = logging.getLogger("pakfire")

import base

from constants import *

class Config(object):
	def __init__(self, type=None):
		self.type = type

		self._config = {
			"debug" : False,
			"logfile" : "/var/log/pakfire.log",
			"source_download_url" : SOURCE_DOWNLOAD_URL,
			"local_build_repo_path" : LOCAL_BUILD_REPO_PATH,
		}

		self._config_repos = {}
		self._distro = {}
		self._master = {}
		self._slave = {}
		self._files = []

		# Read default configuration files
		for file in self.config_files:
			self.read(file)

	def dump(self):
		log.debug("Configuration:")
		for k, v in self._config.items():
			log.debug(" %s : %s" % (k, v))

		log.debug("Loaded from files:")
		for f in self._files:
			log.debug(" %s" % f)

	def read(self, filename):
		# If filename does not exist we return silently
		if not filename or not os.path.exists(filename):
			return

		filename = os.path.abspath(filename)

		# If the file was already loaded, we return silently, too
		if filename in self._files:
			return

		log.debug("Reading configuration file: %s" % filename)

		config = ConfigParser()
		config.read(filename)

		# Read the main section from the file if any
		if "main" in config.sections():
			for k,v in config.items("main"):
				self._config[k] = v
			config.remove_section("main")

		# Read distribution information from the file
		if "distro" in config.sections():
			for k,v in config.items("distro"):
				self._distro[k] = v
			config.remove_section("distro")

		# Read master settings from file
		if "master" in config.sections():
			for k,v in config.items("master"):
				self._master[k] = v
			config.remove_section("master")

		# Read slave settings from file
		if "slave" in config.sections():
			for k,v in config.items("slave"):
				self._slave[k] = v
			config.remove_section("slave")

		# Read repository definitions
		for section in config.sections():
			if not self._config_repos.has_key(section):
				self._config_repos[section] = {}

			options = {}
			for option in config.options(section):
				options[option] = config.get(section, option)

			self._config_repos[section].update(options)

		self._files.append(filename)

	def get(self, key, default=None):
		return self._config.get(key, default)

	def set(self, key, val):
		log.debug("Updating configuration parameter: %s = %s" % (key, val))
		self._config[key] = val

	def update(self, values):
		"""
			This function takes a dictionary which configuration
			parameters and applies them to the configuration.
		"""
		for key, val in values.items():
			self.set(key, val)

	def get_repos(self):
		return self._config_repos.items()

	@property
	def config_files(self):
		files = []

		if self.type == "builder":
			path = os.getcwd()

			while not path == "/":
				_path = os.path.join(path, "config")
				if os.path.exists(_path):
					break

				_path = None
				path = os.path.dirname(path)

			if _path:
				files.append(os.path.join(_path, "pakfire.conf"))
				files.append(os.path.join(_path, "default.conf"))

			# Remove non-existant files
			for f in files:
				if not os.path.exists(f):
					files.remove(f)

		if not files:
			# Return system configuration files
			files += [CONFIG_FILE]

			for f in os.listdir(CONFIG_DIR):
				# Skip all files with wrong extensions.
				if not f.endswith(CONFIG_DIR_EXT):
					continue

				# Create absolute path.
				f = os.path.join(CONFIG_DIR, f)
				files.append(f)

		return files

	@property
	def host_arch(self):
		"""
			Return the architecture of the host we are running on.
		"""
		return os.uname()[4]

	@property
	def supported_arches(self):
		host_arches = {
			# x86
			"x86_64"   : [ "x86_64", ],
			"i686"     : [ "i686", "x86_64", ],
			"i586"     : [ "i586", "i686", "x86_64", ],
			"i486"     : [ "i486", "i586", "i686", "x86_64", ],

			# ARM
			"armv5tel" : [ "armv5tel", "armv5tejl", ],
			"armv7hl " : [ "armv7l", ],
		}

		for host, can_be_built in host_arches.items():
			if self.host_arch in can_be_built:
				yield host

	def host_supports_arch(self, arch):
		"""
			Check if this host can build for the target architecture "arch".
		"""
		return arch in self.supported_arches
