#!/usr/bin/python

import logging

import solver
import satsolver

import pakfire.packages as packages

from local import RepositoryDir, RepositoryBuild, RepositoryLocal
from oddments import RepositoryDummy
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
			self.__repo[name].enabled = True
		except KeyError:
			pass

	def disable_repo(self, name):
		try:
			self.__repo[name].enabled = False
		except KeyError:
			pass

	def update(self, force=False):
		logging.debug("Updating all repository indexes (force=%s)" % force)

		# update all indexes if necessary or forced
		for repo in self:
			repo.update(force=force)

	def whatprovides(self, what):
		for solv in self.pool.providers(what):
			yield packages.SolvPackage(self.pakfire, solv)

	def search(self, what):
		raise NotImplementedError

