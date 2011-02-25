#!/usr/bin/python

import fnmatch
import logging
import os
import shutil
import stat
import time

from ConfigParser import ConfigParser

import base
import database
import downloader
import index
import packages
import util

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
		return cmp(self.priority * -1, other.priority * -1) or \
			cmp(self.name, other.name)

	@property
	def priority(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Say if a repository is a local one or remotely located.

			Used to check if we need to download files.
		"""
		return False

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
	def __init__(self, pakfire, name, description, path):
		RepositoryFactory.__init__(self, pakfire, name, description)

		# Save location of the repository and create it if not existant.
		self.path = path
		if not os.path.exists(self.path):
			os.makedirs(self.path)

		self.index = index.DatabaseIndex(self.pakfire, self)

	@property
	def local(self):
		# This is obviously local.
		return True

	@property
	def priority(self):
		"""
			The local repository has always a high priority.
		"""
		return 10

	# XXX need to implement better get_by_name

	def _collect_packages(self, path):
		logging.info("Collecting packages from %s." % path)

		for dir, subdirs, files in os.walk(path):
			for file in files:
				if not file.endswith(".%s" % PACKAGE_EXTENSION):
					continue

				file = os.path.join(dir, file)

				pkg = packages.BinaryPackage(self.pakfire, self, file)
				self._add_package(pkg)

	def _add_package(self, pkg):
		# XXX gets an instance of binary package and puts it into the
		# repo location if not done yet
		# then: the package gets added to the index

		if not isinstance(pkg, packages.BinaryPackage):
			raise Exception

		repo_filename = os.path.join(self.path, os.path.basename(pkg.filename))

		# Do we need to copy the package files?
		copy = True

		pkg_exists = None
		if os.path.exists(repo_filename):
			pkg_exists = packages.BinaryPackage(self.pakfire, self, repo_filename)

			# If package in the repo is equivalent to the given one, we can
			# skip any further processing.
			if pkg == pkg_exists:
				logging.debug("The package does already exist in this repo: %s" % pkg.friendly_name)
				copy = False

		if copy:
			logging.debug("Copying package '%s' to repository." % pkg.friendly_name)
			repo_dirname = os.path.dirname(repo_filename)
			if not os.path.exists(repo_dirname):
				os.makedirs(repo_dirname)

			# Try to use a hard link if possible, if we cannot do that we simply
			# copy the file.
			try:
				os.link(pkg.filename, repo_filename)
			except OSError:
				shutil.copy2(pkg.filename, repo_filename)

		# Create new package object, that is connected to this repository
		# and so we can do stuff.
		pkg = packages.BinaryPackage(self.pakfire, self, repo_filename)

		logging.info("Adding package '%s' to repository." % pkg.friendly_name)
		self.index.add_package(pkg)

	def save(self, path=None):
		"""
			Save the index information to path.
		"""
		self.index.save(path)


class InstalledRepository(RepositoryFactory):
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "installed", "Installed packages")

		self.index = index.InstalledIndex(self.pakfire, self)

	@property
	def local(self):
		# This is obviously local.
		return True

	@property
	def priority(self):
		"""
			The installed repository has always the highest priority.
		"""
		return 0


class LocalBuildRepository(LocalRepository):
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "build", "Locally built packages")

		self.path = self.pakfire.config.get("local_build_repo_path")
		if not os.path.exists(self.path):
			os.makedirs(self.path)

		self.index = index.DirectoryIndex(self.pakfire, self, self.path)

	@property
	def priority(self):
		return 20000


class RepositoryCache(object):
	"""
		An object that is able to cache all data that is loaded from a
		remote repository.
	"""

	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

		self.create()

	@property
	def path(self):
		return os.path.join(REPO_CACHE_DIR, self.pakfire.distro.release, \
			self.repo.name, self.repo.arch)

	def abspath(self, path):
		return os.path.join(self.path, path)

	def create(self):
		"""
			Create all necessary directories.
		"""
		for path in ("mirrors", "packages", "repodata"):
			path = self.abspath(path)

			if not os.path.exists(path):
				os.makedirs(path)

	def exists(self, filename):
		"""
			Returns True if a file exists and False if it doesn't.
		"""
		return os.path.exists(self.abspath(filename))

	def age(self, filename):
		"""
			Returns the age of a downloaded file in minutes.
			i.e. the time from download until now.
		"""
		if not self.exists(filename):
			return None

		filename = self.abspath(filename)

		# Creation time of the file
		ctime = os.stat(filename)[stat.ST_CTIME]

		return (time.time() - ctime) / 60

	def open(self, filename, *args, **kwargs):
		filename = self.abspath(filename)

		return open(filename, *args, **kwargs)

	def verify(self, filename, hash1):
		"""
			Return a bool that indicates if a file matches the given hash.
		"""
		return util.calc_hash1(self.abspath(filename)) == hash1

	def remove(self, filename):
		"""
			Remove a file from cache.
		"""
		if not self.exists(filename):
			return

		filename = self.abspath(filename)
		os.unlink(filename)


class RemoteRepository(RepositoryFactory):
	def __init__(self, pakfire, name, description, url, mirrorlist, gpgkey, enabled):
		RepositoryFactory.__init__(self, pakfire, name, description)

		self.url, self.gpgkey = url, gpgkey
		self.mirrorlist = mirrorlist

		if enabled in (True, 1, "1", "yes", "y"):
			self.enabled = True
		else:
			self.enabled = False

		# A place to cache the download grabber for this repo.
		self.__grabber = None

		# Create a cache for the repository where we can keep all temporary data.
		self.cache = RepositoryCache(self.pakfire, self)

		# Initialize mirror servers.
		self.mirrors = downloader.MirrorList(self.pakfire, self)

		if self.local:
			self.index = index.DirectoryIndex(self.pakfire, self, self.url)
		else:
			self.index = index.DatabaseIndex(self.pakfire, self)

		logging.debug("Created new repository(name='%s', url='%s', enabled='%s')" % \
			(self.name, self.url, self.enabled))

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.url)

	@property
	def local(self):
		# If files are located somewhere in the filesystem we assume it is
		# local.
		if self.url.startswith("file://"):
			return True

		# Otherwise not.
		return False

	@property
	def arch(self):
		return self.pakfire.distro.arch

	@property
	def path(self):
		if self.local:
			return self.url[7:]

		return self.cache.path

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

	def update_index(self, force=False):
		if self.index:
			self.index.update(force=force)

	def save_index(self, path=None):
		self.index.save(path)

	#def get_all(self, requires):
	#	for pkg in self.index.get_all():
	#		if pkg.does_provide(requires):
	#			yield pkg

