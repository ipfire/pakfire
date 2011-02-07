#!/usr/bin/python

import fnmatch
import logging
import os

from ConfigParser import ConfigParser

from urlgrabber.grabber import URLGrabber
from urlgrabber.mirror import MGRandomOrder
from urlgrabber.progress import TextMultiFileMeter

import base
import database
import index

from constants import *

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

		# Create the local repository
		self.local = LocalRepository(self.pakfire)
		self.add_repo(self.local)

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

	def update_indexes(self, force=False):
		logging.debug("Updating all repository indexes (force=%s)" % force)

		# XXX update all indexes if necessary or forced
		for repo in self.enabled:
			repo.update_index(force=force)

	def get_all(self):
		for repo in self.enabled:
			for pkg in repo.get_all():
				yield pkg

	def get_by_name(self, name):
		for repo in self.enabled:
			for pkg in repo.get_by_name(name):
				yield pkg

	def get_by_glob(self, pattern):
		for repo in self.enabled:
			for pkg in repo.get_by_glob(pattern):
				yield pkg

	def get_by_provides(self, requires):
		for repo in self.enabled:
			for pkg in repo.get_by_provides(requires):
				yield pkg

	def search(self, pattern):
		pkg_names = []

		for repo in self.enabled:
			for pkg in repo.search(pattern):
				if pkg.name in pkg_names:
					continue

				pkg_names.append(pkg.name)
				yield pkg


class RepositoryFactory(object):
	def __init__(self, pakfire, name, description):
		self.pakfire = pakfire

		self.name, self.description = name, description

		# All repositories are enabled by default
		self.enabled = True

		# Add link to distro object
		self.distro = pakfire.distro #distro.Distribution()

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __cmp__(self, other):
		return cmp(self.priority, other.priority) or cmp(self.name, other.name)

	@property
	def priority(self):
		raise NotImplementedError

	def update_index(self, force=False):
		"""
			A function that is called to update the local data of
			the repository.
		"""
		pass

	def get_all(self):
		"""
			Simply returns an instance of every package in this repository.
		"""
		for pkg in self.packages:
			yield pkg

	def get_by_name(self, name):
		for pkg in self.packages:
			if pkg.name == name:
				yield pkg

	def get_by_glob(self, pattern):
		"""
			Returns a list of all packages that names match the glob pattern
			that is provided.
		"""
		for pkg in self.packages:
			if fnmatch.fnmatch(pkg.name, pattern):
				yield pkg

	def get_by_provides(self, requires):
		"""
			Returns a list of all packages that offer a matching "provides"
			of the given "requires".
		"""
		for pkg in self.packages:
			if pkg.does_provide(requires):
				yield pkg

	def search(self, pattern):
		"""
			Returns a list of packages, that match the given pattern,
			which can be either a part of the name, summary or description
			or can be a glob pattern that matches one of these.
		"""
		for pkg in self.packages:
			for item in (pkg.name, pkg.summary, pkg.description):
				if pattern.lower() in item.lower() or \
						fnmatch.fnmatch(item, pattern):
					yield pkg

	@property
	def packages(self):
		"""
			Returns all packages.
		"""
		return self.index.packages


class DummyRepository(RepositoryFactory):
	"""
		Just a dummy repository that actually does nothing.
	"""
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "dummy",
			"This is a dummy repository.")


class FileSystemRepository(RepositoryFactory):
	"""
		Dummy repository to indicate that a specific package came from the
		filesystem.
	"""
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "filesystem",
			"Filesystem repository")


class LocalRepository(RepositoryFactory):
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "installed", "Installed packages")

		self.path = os.path.join(self.pakfire.path, PACKAGES_DB)

		self.db = database.LocalPackageDatabase(self.pakfire, self.path)

		self.index = index.InstalledIndex(self.pakfire, self, self.db)

	@property
	def priority(self):
		"""
			The local repository has always the highest priority.
		"""
		return 0

	# XXX need to implement better get_by_name



class RemoteRepository(RepositoryFactory):
	def __init__(self, pakfire, name, description, url, gpgkey, enabled):
		RepositoryFactory.__init__(self, pakfire, name, description)

		self.url, self.gpgkey = url, gpgkey

		if enabled in (True, 1, "1", "yes", "y"):
			self.enabled = True
		else:
			self.enabled = False

		if self.url.startswith("file://"):
			self.index = index.DirectoryIndex(self.pakfire, self, self.url[7:])
		
		else:
			self.index = None

		logging.debug("Created new repository(name='%s', url='%s', enabled='%s')" % \
			(self.name, self.url, self.enabled))

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.url)

	@property
	def priority(self):
		priority = 100

		url2priority = {
			"file://" : 50,
			"http://" : 75,
		}

		for url, prio in url2priority.items():
			if self.url.startswith(url):
				priority = prio
				break

		return priority

	@property
	def mirrorlist(self):
		# XXX
		return [
			"http://mirror0.ipfire.org/",
		]

	def fetch_file(self, filename):
		grabber = URLGrabber(
			progress_obj = TextMultiFileMeter(),
		)

		mg = MGRandomOrder(grabber, self.mirrorlist)

		# XXX Need to say destination here.
		mg.urlgrab(filename)

	def update_index(self, force=False):
		if self.index:
			self.index.update(force=force)

	#def get_all(self, requires):
	#	for pkg in self.index.get_all():
	#		if pkg.does_provide(requires):
	#			yield pkg

