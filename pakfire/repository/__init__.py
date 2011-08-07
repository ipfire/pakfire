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

import logging

import pakfire.packages as packages

from base import RepositoryDummy
from local import RepositoryDir, RepositoryBuild, RepositoryLocal
from remote import RepositorySolv

class Repositories(object):
	"""
		Class that loads all repositories from the configuration files.

		This is the place where repositories can be activated or deactivated.
	"""

	def __init__(self, pakfire, enable_repos=None, disable_repos=None):
		self.pakfire = pakfire

		self.config = pakfire.config
		self.distro = pakfire.distro

		# Place to store the repositories
		self.__repos = {}

		# Create a dummy repository
		self.dummy = RepositoryDummy(self.pakfire)

		# Create the local repository
		self.local = RepositoryLocal(self.pakfire)
		self.add_repo(self.local)

		# If we running in build mode, we include our local build repository.
		if self.pakfire.builder:
			self.local_build = RepositoryBuild(self.pakfire)
			self.add_repo(self.local_build)

		for repo_name, repo_args in self.config.get_repos():
			self._parse(repo_name, repo_args)

		# Enable all repositories here as demanded on commandline
		if enable_repos:
			for repo in enable_repos:
				self.enable_repo(repo)

		# Disable all repositories here as demanded on commandline
		if disable_repos:
			for repo in disable_repos:
				self.disable_repo(repo)

		# Update all indexes of the repositories (not force) so that we will
		# always work with valid data.
		self.update()

	def __iter__(self):
		repositories = self.__repos.values()
		repositories.sort()

		return iter(repositories)

	def __len__(self):
		"""
			Return the count of enabled repositories.
		"""
		return len([r for r in self if r.enabled])

	@property
	def pool(self):
		return self.pakfire.pool

	def _parse(self, name, args):
		# XXX need to make variable expansion

		_args = {
			"name" : name,
			"enabled" : True,
			"gpgkey" : None,
			"mirrorlist" : None,
		}
		_args.update(args)

		repo = RepositorySolv(self.pakfire, **_args)

		self.add_repo(repo)

	def add_repo(self, repo):
		if self.__repos.has_key(repo.name):
			raise Exception, "Repository with that name does already exist."

		self.__repos[repo.name] = repo

	def rem_repo(self, repo):
		"""
			Remove the given repository from the global repository set.
		"""
		try:
			del self.__repos[repo.name]
		except KeyError:
			logging.debug("Repository that was to be removed does not exist: %s" % repo.name)

	def get_repo(self, name):
		"""
			Get the repository with the given name, if not available, return
			the dummy repository.
		"""
		try:
			return self.__repos[name]
		except KeyError:
			return self.dummy

	def enable_repo(self, name):
		try:
			self.__repos[name].enabled = True
		except KeyError:
			pass

	def disable_repo(self, name):
		try:
			self.__repos[name].enabled = False
		except KeyError:
			pass

	def update(self, force=False):
		logging.debug("Updating all repository indexes (force=%s)" % force)

		# update all indexes if necessary or forced
		for repo in self:
			repo.update(force=force)

	def whatprovides(self, what):
		what = self.pakfire.create_relation(what)

		for solv in self.pool.providers(what):
			yield packages.SolvPackage(self.pakfire, solv)

	def clean(self):
		logging.info("Cleaning up all repository caches...")

		for repo in self:
			repo.clean()
