#!/usr/bin/python

import json
import logging
import os
import random
import shutil

import database
import downloader
import metadata
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


class InstalledIndex(Index):
	def __init__(self, pakfire, repo):
		Index.__init__(self, pakfire, repo)

		# Open the database.
		self.db = database.LocalPackageDatabase(self.pakfire)

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
		# XXX DEPRECATED
		self.db.close()

		# Calculate a filename that is based on the hash of the file
		# (just to trick proxies, etc.)
		filename = util.calc_hash1(self.db.filename) + "-packages.db"

		# Copy the database to the right place.
		shutil.copy2(self.db.filename, os.path.join(self.repo.path, filename))

		# Reopen the database.
		self.db = database.RemotePackageDatabase(self.pakfire, self.db.filename)


class DatabaseIndex(InstalledIndex):
	def __init__(self, pakfire, repo):
		Index.__init__(self, pakfire, repo)

		# Initialize with no content.
		self.db, self.metadata = None, None

	def _update_metadata(self, force):
		# Shortcut to repository cache.
		cache = self.repo.cache

		filename = METADATA_DOWNLOAD_FILE

		# Marker if we need to do the download.
		download = True

		# Marker for the current metadata.
		old_metadata = None

		if not force:
			# Check if file does exists and is not too old.
			if cache.exists(filename):
				age = cache.age(filename)
				if age and age < TIME_10M:
					download = False
					logging.debug("Metadata is recent enough. I don't download it again.")

				# Open old metadata for comparison.
				old_metadata = metadata.Metadata(self.pakfire, self,
					cache.abspath(filename))

		if download:
			logging.debug("Going to (re-)download the repository metadata.")

			# Initialize a grabber for download.
			grabber = downloader.MetadataDownloader()
			grabber = self.repo.mirrors.group(grabber)

			data = grabber.urlread(filename, limit=METADATA_DOWNLOAD_LIMIT)

			# Parse new metadata for comparison.
			new_metadata = metadata.Metadata(self.pakfire, self, metadata=data)

			if old_metadata and new_metadata < old_metadata:
				logging.warning("The downloaded metadata was less recent than the current one. Trashing that.")

			else:
				# We explicitely rewrite the metadata if it is equal to have
				# a new timestamp and do not download it over and over again.
				with cache.open(filename, "w") as o:
					o.write(data)

		# Parse the metadata that we just downloaded or load it from cache.
		self.metadata = metadata.Metadata(self.pakfire, self,
			cache.abspath(filename))

	def _update_database(self, force):
		# Shortcut to repository cache.
		cache = self.repo.cache

		# Construct cache and download filename.
		filename = os.path.join(METADATA_DOWNLOAD_PATH, self.metadata.database)

		if not cache.exists(filename):
			# Initialize a grabber for download.
			grabber = downloader.DatabaseDownloader(
				text = _("%s: package database") % self.repo.name,
			)
			grabber = self.repo.mirrors.group(grabber)

			data = grabber.urlread(filename)

			with cache.open(filename, "w") as o:
				o.write(data)

			# XXX possibly, the database needs to be decompressed

		# (Re-)open the database.
		self.db = database.RemotePackageDatabase(self.pakfire,
			cache.abspath(filename))

	def update(self, force=False):
		"""
			Download the repository metadata and the package database.
		"""

		# At first, update the metadata.
		self._update_metadata(force)

		# Then, we download the database eventually.
		self._update_database(force)

		# XXX this code needs lots of work:
		# XXX   * make checks for downloads (hashsums)
		# XXX   * check the metadata content
		# XXX   * use compression

