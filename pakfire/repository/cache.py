#!/usr/bin/python

import os
import stat
import time

import pakfire.util as util
from pakfire.constants import *

class RepositoryCache(object):
	"""
		An object that is able to cache all data that is loaded from a
		remote repository.
	"""

	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

		self.__created = None

	@property
	def created(self):
		"""
			Tells us, if the cache was already created.
		"""
		if self.__created is None:
			self.__created = os.path.exists(self.path)

		return self.__created

	@property
	def path(self):
		return os.path.join(REPO_CACHE_DIR, self.pakfire.distro.release, \
			self.repo.name, self.repo.arch)

	def abspath(self, path, create=True):
		if create:
			self.create()

		return os.path.join(self.path, path)

	def create(self):
		"""
			Create all necessary directories.
		"""
		# Do nothing, if the cache has already been created.
		if self.created:
			return

		for path in ("mirrors", "packages", "repodata"):
			path = self.abspath(path, create=False)

			if not os.path.exists(path):
				os.makedirs(path)

		self.__created = True

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

