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

import glob
import os
import re

import logging
log = logging.getLogger("pakfire")

from .. import config
from .. import packages

from .base import RepositoryDummy
from .local import RepositoryDir, RepositoryBuild
from .remote import RepositoryRemote
from .system import RepositorySystem

from ..i18n import _

class Repositories(object):
	"""
		Class that loads all repositories from the configuration files.

		This is the place where repositories can be activated or deactivated.
	"""

	def __init__(self, pakfire):
		self.pakfire = pakfire

		# Place to store the repositories
		self.__repos = {}

		# Create a dummy repository
		from . import base
		self.dummy = base.RepositoryDummy(self.pakfire)

		# Create the local repository.
		self.local = self.pakfire.installed_repo = RepositorySystem(self.pakfire)
		self.add_repo(self.local)

		# If we running in build mode, we include our local build repository.
		if self.pakfire.mode == "builder":
			self.local_build = RepositoryBuild(self.pakfire)
			self.add_repo(self.local_build)

		self._load_from_configuration(self.pakfire.config)

	def __iter__(self):
		repositories = list(self.__repos.values())
		repositories.sort()

		return iter(repositories)

	def __len__(self):
		"""
			Return the count of enabled repositories.
		"""
		return len([r for r in self if r.enabled])

	def refresh(self):
		"""
			Refreshes all repositories
		"""
		for repo in self:
			if repo.enabled:
				repo.refresh()

	@property
	def distro(self):
		return self.pakfire.distro

	def load_configuration(self, *paths):
		c = config.Config()

		for path in paths:
			# Read directories
			if os.path.isdir(path):
				for file in glob.glob("%s/*.repo" % path):
					c.read(file)

			# Read files
			else:
				c.read(path)

		self._load_from_configuration(c)

	def _load_from_configuration(self, config):
		# Add all repositories that have been found
		for name, settings in config.get_repos():
			self._parse(name, settings)

	def _parse(self, name, args):
		_args = {
			"name" : name,
			"enabled" : True,
			"gpgkey" : None,
			"mirrors" : None,
		}
		_args.update(args)

		# Handle variable expansion.
		replaces = {
			"name" : name,
			"arch" : self.pakfire.arch,
		}

		for k, v in list(_args.items()):
			# Skip all non-strings.
			if not type(v) == type("a"):
				continue

			while True:
				m = re.search(packages.lexer.LEXER_VARIABLE, v)

				# If we cannot find a match, we are done.
				if not m:
					_args[k] = v
					break

				# Get the name of the variable.
				(var,) = m.groups()

				# Replace the variable with its value.
				v = v.replace("%%{%s}" % var, replaces.get(var, ""))

		repo = RepositoryRemote(self.pakfire, **_args)
		self.add_repo(repo)

	def add_repo(self, repo):
		if repo.name in self.__repos:
			raise Exception("Repository with that name does already exist: %s" % repo.name)

		self.__repos[repo.name] = repo

	def rem_repo(self, repo):
		"""
			Remove the given repository from the global repository set.
		"""
		try:
			del self.__repos[repo.name]
		except KeyError:
			log.debug("Repository that was to be removed does not exist: %s" % repo.name)

	def get_repo(self, name):
		"""
			Get the repository with the given name, if not available, return
			the dummy repository.
		"""
		try:
			return self.__repos[name]
		except KeyError:
			return self.dummy

	def clean(self):
		log.info("Cleaning up all repository caches...")

		for repo in self:
			repo.clean()
