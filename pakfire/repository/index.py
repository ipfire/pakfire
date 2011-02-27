#!/usr/bin/python

import json
import logging
import lzma
import os
import random
import shutil
import time
import zlib

import database
import downloader
import metadata

import pakfire.packages as packages
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class Index(object):
	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

		self._packages = []

	@property
	def arch(self):
		return self.pakfire.distro.arch

	def get_all_by_name(self, name):
		for package in self.packages:
			if package.name == name:
				yield package

	def get_by_file(self, filename):
		for pkg in self.packages:
			if filename in pkg.filelist:
				yield pkg

	def get_by_id(self, id):
		raise NotImplementedError

	def get_by_uuid(self, uuid):
		for pkg in self.packages:
			if pkg.uuid == uuid:
				return pkg

	def get_by_provides(self, requires):
		for pkg in self.packages:
			if pkg.does_provide(requires):
				yield pkg

	@property
	def packages(self):
		for pkg in self._packages:
			yield pkg

	def update(self, force=False):
		pass

	def add_package(self, pkg):
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


class DatabaseIndexFactory(Index):
	def __init__(self, pakfire, repo):
		Index.__init__(self, pakfire, repo)

		# Add empty reference to a fictional database.
		self.db = None

		self.open_database()

	def open_database(self):
		raise NotImplementedError

	@property
	def packages(self):
		c = self.db.cursor()
		c.execute("SELECT * FROM packages")

		for pkg in c:
			yield packages.DatabasePackage(self.pakfire, self.repo, self.db, pkg)

		c.close()

	def add_package(self, pkg, reason=None):
		return self.db.add_package(pkg, reason)

	def get_by_id(self, id):
		c = self.db.cursor()
		c.execute("SELECT * FROM packages WHERE id = ? LIMIT 1", (id,))

		ret = None
		for pkg in c:
			ret = packages.DatabasePackage(self.pakfire, self.repo, self.db, pkg)

		c.close()

		return ret

	def get_by_file(self, filename):
		c = self.db.cursor()
		c.execute("SELECT pkg FROM files WHERE name = ?", (filename,))

		for pkg in c:
			yield self.get_by_id(pkg["pkg"])

		c.close()


class InstalledIndex(DatabaseIndexFactory):
	def open_database(self):
		# Open the local package database.
		self.db = database.LocalPackageDatabase(self.pakfire)


class LocalIndex(DatabaseIndexFactory):
	def open_database(self):
		self.db = database.RemotePackageDatabase(self.pakfire, ":memory:")

	def save(self, path=None, compress="xz"):
		"""
			This function saves the database and metadata to path so it can
			be exported to a remote repository.
		"""
		if not path:
			path = self.repo.path

		# Create filenames
		metapath = os.path.join(path, METADATA_DOWNLOAD_PATH)
		db_path  = os.path.join(metapath, METADATA_DATABASE_FILE)
		md_path  = os.path.join(metapath, METADATA_DOWNLOAD_FILE)

		if not os.path.exists(metapath):
			os.makedirs(metapath)

		else:
			# If a database is present, we remove it because we want to start
			# with a clean environment.
			if os.path.exists(db_path):
				os.unlink(db_path)

		# Save the database to path and get the filename.
		self.db.save(db_path)

		# Make a reference to the database file that it will get a unique name
		# so we won't get into any trouble with caching proxies.
		db_hash = util.calc_hash1(db_path)

		db_path2 = os.path.join(os.path.dirname(db_path),
			"%s-%s" % (db_hash, os.path.basename(db_path)))

		# Compress the database.
		if compress:
			i = open(db_path)
			os.unlink(db_path)

			o = open(db_path, "w")

			# Choose a compressor.
			if compress == "xz":
				comp = lzma.LZMACompressor()
			elif compress == "zlib":
				comp = zlib.compressobj(9)

			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(comp.compress(buf))

				buf = i.read(BUFFER_SIZE)

			o.write(comp.flush())

			i.close()
			o.close()

		if not os.path.exists(db_path2):
			shutil.move(db_path, db_path2)
		else:
			os.unlink(db_path)

		# Create a new metadata object and add out information to it.
		md = metadata.Metadata(self.pakfire, self)

		# Save name of the hashed database to the metadata.
		md.database = os.path.basename(db_path2)
		md.database_hash1 = db_hash
		md.database_compression = compress

		# Save metdata to repository.
		md.save(md_path)


class RemoteIndex(DatabaseIndexFactory):
	def open_database(self):
		self.update(force=False)

	def _update_metadata(self, force):
		# Shortcut to repository cache.
		cache = self.repo.cache

		filename = os.path.join(METADATA_DOWNLOAD_PATH, METADATA_DOWNLOAD_FILE)

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

			# decompress the database
			if self.metadata.database_compression:
				# Open input file and remove the file immediately.
				# The fileobj is still open and the data will be removed
				# when it is closed.
				i = cache.open(filename)
				cache.remove(filename)

				# Open output file.
				o = cache.open(filename, "w")

				# Choose a decompessor.
				if self.metadata.database_compression == "xz":
					comp = lzma.LZMADecompressor()

				elif self.metadata.database_compression == "zlib":
					comp = zlib.decompressobj()

				buf = i.read(BUFFER_SIZE)
				while buf:
					o.write(comp.decompress(buf))

					buf = i.read(BUFFER_SIZE)

				o.write(comp.flush())

				i.close()
				o.close()

			# check the hashsum of the downloaded file
			if not util.calc_hash1(cache.abspath(filename)) == self.metadata.database_hash1:
				# XXX an exception is not a very good idea because this file could
				# be downloaded from another mirror. need a better way to handle this.

				# Remove bad file from cache.
				cache.remove(filename)

				raise Exception, "Downloaded file did not match the hashsum. Need to re-download it."

		# (Re-)open the database.
		self.db = database.RemotePackageDatabase(self.pakfire,
			cache.abspath(filename))

	def update(self, force=False):
		"""
			Download the repository metadata and the package database.
		"""

		# Skip the download for local repositories.
		if self.repo.local:
			return

		# At first, update the metadata.
		self._update_metadata(force)

		# Then, we download the database eventually.
		self._update_database(force)

		# XXX this code needs lots of work:
		# XXX   * check the metadata content
