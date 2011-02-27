#!/usr/bin/python

import logging

from installed import InstalledRepository
from local import LocalRepository, LocalBuildRepository
from oddments import DummyRepository
from remote import RemoteRepository

class Repositories(object):
	"""
		Class that loads all repositories from the configuration files.

		This is the place where repositories can be activated or deactivated.
	"""

	def __init__(self, pakfire):
		self.pakfire = pakfire

		self.config = pakfire.config
		self.distro = pakfire.distro

		# Place to store the repositories
		self._repos = []

		# Create a dummy repository
		self.dummy = DummyRepository(self.pakfire)

		# Create the local repository
		self.local = InstalledRepository(self.pakfire)
		self.add_repo(self.local)

		# If we running in build mode, we include our local build repository.
		if self.pakfire.builder:
			self.local_build = LocalBuildRepository(self.pakfire)
			self.add_repo(self.local_build)

		for repo_name, repo_args in self.config.get_repos():
			self._parse(repo_name, repo_args)

	def __len__(self):
		"""
			Return the count of enabled repositories.
		"""
		i = 0
		for repo in self.enabled:
			i += 1

		return i

	def _parse(self, name, args):
		# XXX need to make variable expansion

		_args = {
			"name" : name,
			"enabled" : True,
			"gpgkey" : None,
			"mirrorlist" : None,
		}
		_args.update(args)

		repo = RemoteRepository(self.pakfire, **_args)

		self.add_repo(repo)

	def add_repo(self, repo):
		self._repos.append(repo)
		self._repos.sort()

	@property
	def enabled(self):
		for repo in self._repos:
			if not repo.enabled:
				continue

			yield repo

	def disable_repo(self, name):
		for repo in self.enabled:
			if repo.name == name:
				logging.debug("Disabled repository '%s'" % repo.name)
				repo.enabled = False
				continue

	def update(self, force=False):
		logging.debug("Updating all repository indexes (force=%s)" % force)

		# XXX update all indexes if necessary or forced
		for repo in self.enabled:
			repo.update(force=force)

	#def get_all(self):
	#	for repo in self.enabled:
	#		for pkg in repo.get_all():
	#			yield pkg

	def get_by_name(self, name):
		for repo in self.enabled:
			for pkg in repo.get_by_name(name):
				yield pkg

	def get_by_glob(self, pattern):
		for repo in self.enabled:
			for pkg in repo.get_by_glob(pattern):
				yield pkg

	def get_by_provides(self, requires):
		if requires.type == "file":
			for pkg in self.get_by_file(requires.requires):
				yield pkg

		else:
			for repo in self.enabled:
				for pkg in repo.get_by_provides(requires):
					yield pkg

	def get_by_file(self, filename):
		for repo in self.enabled:
			for pkg in repo.get_by_file(filename):
				yield pkg

	def search(self, pattern):
		pkg_names = []

		for repo in self.enabled:
			for pkg in repo.search(pattern):
				if pkg.name in pkg_names:
					continue

				pkg_names.append(pkg.name)
				yield pkg
