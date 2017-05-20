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

from . import distro

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

		# Silently return if nothing is found
		if not os.path.exists(path):
			return

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

	@property
	def distro(self):
		return distro.Distribution(self._config["distro"])

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
