#!/usr/bin/python

import json
import logging
import os
import random
import shutil

import database
import downloader
import packages
import repository
import util

from constants import *
from i18n import _

class Index(object):
	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

		self.arch = self.pakfire.distro.arch # XXX ???

		self._packages = []

	def get_all(self):
		for package in self.packages:
			yield package

	def get_all_by_name(self, name):
		for package in self.packages:
			if package.name == name:
				yield package

	def get_latest_by_name(self, name):
		p = [p for p in self.get_all_by_name(name)]
		if not p:
			return

		# Get latest version of the package to the bottom of
		# the list.
		p.sort()

		# Return the last one.
		return p[-1]

	@property
	def packages(self):
		for pkg in self._packages:
			yield pkg

	@property
	def package_names(self):
		names = []
		for name in [p.name for p in self.packages]:
			if not name in names:
				names.append(name)

		return sorted(names)

	def update(self, force=False):
		raise NotImplementedError

	def add_package(self, pkg):
		raise NotImplementedError

	def tag_db(self):
		raise NotImplementedError


class DirectoryIndex(Index):
	def __init__(self, pakfire, repo, path):
		if path.startswith("file://"):
			path = path[7:]
		self.path = path

		Index.__init__(self, pakfire, repo)

		# Always update this because it will otherwise contain no data
		self.update(force=True)

	def update(self, force=False):
		logging.debug("Updating repository index '%s' (force=%s)" % (self.path, force))

		# Do nothing if the update is not forced but populate the database
		# if no packages are present.
		if not force and self._packages:
			return

		# If we update the cache, we clear it first.
		self._packages = []

		for dir, subdirs, files in os.walk(self.path):
			for file in files:
				# Skip files that do not have the right extension
				if not file.endswith(".%s" % PACKAGE_EXTENSION):
					continue

				file = os.path.join(dir, file)

				package = packages.BinaryPackage(self.pakfire, self.repo, file)

				if not package.arch in (self.arch, "noarch"):
					logging.warning("Skipped package with wrong architecture: %s (%s)" \
						% (package.filename, package.arch))
					continue

				self._packages.append(package)

	def save(self, path=None):
		if not path:
			path = self.path

		path = os.path.join(path, "index.db")

		db = database.PackageDatabase(self.pakfire, path)

		for pkg in self.packages:
			db.add_package(pkg)

		db.close()


class DatabaseIndex(Index):
	def __init__(self, pakfire, repo):
		Index.__init__(self, pakfire, repo)

		self.db = None

		if isinstance(repo, repository.InstalledRepository):
			self.db = database.LocalPackageDatabase(self.pakfire)

		else:
			# Generate path to database file.
			filename = os.path.join(repo.path, ".index.db.%s" % random.randint(0, 1024))
			self.db = database.RemotePackageDatabase(self.pakfire, filename)

	@property
	def local(self):
		pass

	def update(self, force=False):
		"""
			Download the repository metadata and the package database.
		"""

		# XXX this code needs lots of work:
		# XXX   * fix the hardcoded paths
		# XXX   * make checks for downloads (filesize, hashsums)
		# XXX   * don't download the package database in place
		# XXX   * check the metadata content
		# XXX   * use compression

		# Shortcut to repository cache.
		cache = self.repo.cache

		cache_filename = "metadata/repomd.json"

		# Marker if we need to do the download.
		download = True

		# Check if file does exists and is not too old.
		if cache.exists(cache_filename):
			age = cache.age(cache_filename)
			if age and age < TIME_10M:
				download = False

		if download:
			# Initialize a grabber for download.
			grabber = downloader.MetadataDownloader()
			grabber = self.repo.mirrors.group(grabber)

			# XXX do we need limit here for security reasons?
			metadata = grabber.urlread("repodata/repomd.json")

			with cache.open(cache_filename, "w") as o:
				o.write(metadata)

		# Parse the metadata that we just downloaded or opened from cache.
		f = cache.open(cache_filename)
		metadata = json.loads(f.read())
		f.close()

		# Get the filename of the package database from the metadata.
		download_filename = "repodata/%s" % metadata.get("package_database")

		cache_filename = "metadata/packages.db"

		if not cache.exists(cache_filename):
			# Initialize a grabber for download.
			grabber = downloader.DatabaseDownloader(
				text = _("%s: package database") % self.repo.name,
			)
			grabber = self.repo.mirrors.group(grabber)

			i = grabber.urlopen(download_filename)
			o = cache.open(cache_filename, "w")

			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(buf)
				buf = i.read(BUFFER_SIZE)

			i.close()
			o.close()

			# XXX possibly, the database needs to be decompressed

		# Reopen the database
		self.db = database.RemotePackageDatabase(self.pakfire, cache.abspath(cache_filename))

	def __get_from_cache(self, pkg):
		"""
			Check if package is already in cache and return an instance of
			BinaryPackage instead.
		"""
		if hasattr(self.repo, "cache"):
			filename = os.path.join("packages", os.path.basename(pkg.filename))

			if self.repo.cache.exists(filename):
				filename = self.repo.cache.abspath(filename)

				pkg = packages.BinaryPackage(self.pakfire, self.repo, filename)

		return pkg

	def get_all_by_name(self, name):
		c = self.db.cursor()
		c.execute("SELECT * FROM packages WHERE name = ?", name)

		for pkg in c:
			pkg = package.DatabasePackage(self.pakfire, self.repo, self.db, pkg)

			# Try to get package from cache.
			yield self.__get_from_cache(pkg)

		c.close()

	@property
	def package_names(self):
		c = self.db.cursor()
		c.execute("SELECT DISTINCT name FROM packages ORDER BY name")

		for pkg in c:
			yield pkg["name"]

		c.close()

	@property
	def packages(self):
		c = self.db.cursor()
		c.execute("SELECT * FROM packages")

		for pkg in c:
			pkg = packages.DatabasePackage(self.pakfire, self.repo, self.db, pkg)

			# Try to get package from cache.
			yield self.__get_from_cache(pkg)

		c.close()

	def add_package(self, pkg, reason=None):
		return self.db.add_package(pkg, reason)

	def tag_db(self):
		self.db.close()

		# Calculate a filename that is based on the hash of the file
		# (just to trick proxies, etc.)
		filename = util.calc_hash1(self.db.filename) + "-packages.db"

		# Copy the database to the right place.
		shutil.copy2(self.db.filename, os.path.join(self.repo.path, filename))

		# Reopen the database.
		self.db = database.RemotePackageDatabase(self.pakfire, self.db.filename)


# XXX maybe this can be removed later?
class InstalledIndex(DatabaseIndex):
	pass

