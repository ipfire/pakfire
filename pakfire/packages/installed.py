#!/usr/bin/python

import os

import pakfire.downloader

from base import Package
from binary import BinaryPackage

from pakfire.constants import *

class DatabasePackage(Package):
	type = "db"

	def __init__(self, pakfire, repo, db, data):
		Package.__init__(self, pakfire, repo)

		self.db = db

		self._data = {}

		for key in data.keys():
			self._data[key] = data[key]

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.friendly_name)

	@property
	def metadata(self):
		return self._data

	@property
	def id(self):
		id = self.metadata.get("id")
		if not id:
			id = 0

		return id

	@property
	def name(self):
		return self.metadata.get("name")

	@property
	def version(self):
		return self.metadata.get("version")

	@property
	def release(self):
		return self.metadata.get("release")

	@property
	def epoch(self):
		epoch = self.metadata.get("epoch", 0)

		return int(epoch)

	@property
	def arch(self):
		return self.metadata.get("arch")

	@property
	def maintainer(self):
		return self.metadata.get("maintainer")

	@property
	def license(self):
		return self.metadata.get("license")

	@property
	def summary(self):
		return self.metadata.get("summary")

	@property
	def description(self):
		return self.metadata.get("description")

	@property
	def group(self):
		return self.metadata.get("group")

	@property
	def build_date(self):
		return self.metadata.get("build_date")

	@property
	def build_time(self):
		return self.metadata.get("build_time")

	@property
	def build_host(self):
		return self.metadata.get("build_host")

	@property
	def build_id(self):
		return self.metadata.get("build_id")

	@property
	def uuid(self):
		return self.metadata.get("uuid")

	@property
	def size(self):
		return self.metadata.get("size", 0)

	@property
	def provides(self):
		if not hasattr(self, "__provides"):
			# Get automatic provides
			provides = self._provides

			# Add other provides
			for prov in self.metadata.get("provides", "").split():
				if not prov in provides:
					provides.append(prov)

			self.__provides = provides

		return self.__provides

	@property
	def requires(self):
		requires = self.metadata.get("requires")
		
		if requires:
			return requires.split()

		return []

	@property
	def conflicts(self):
		conflicts = self.metadata.get("conflicts")

		if conflicts:
			return conflicts.split()

		return []

	@property
	def hash1(self):
		return self.metadata.get("hash1")

	@property
	def scriptlet(self):
		return self.metadata.get("scriptlet")

	@property
	def filename(self):
		return self.metadata.get("filename") # XXX basename?

	@property
	def filelist(self):
		if not hasattr(self, "__filelist"):
			c = self.db.cursor()
			c.execute("SELECT name FROM files WHERE pkg = ?", (self.id,))

			self.__filelist = []
			for f in c:
				self.__filelist.append(f["name"])

			c.close()

		return self.__filelist

	def _does_provide_file(self, requires):
		"""
			A faster version to find a file in the database.
		"""
		c = self.db.cursor()
		c.execute("SELECT * FROM files WHERE name GLOB ? AND pkg = ?",
			(requires.requires, self.id))

		ret = False
		for pkg in c:
			ret = True
			break

		c.close()

		return ret

	def download(self, text=""):
		"""
			Downloads the package from repository and returns a new instance
			of BinaryPackage.
		"""
		# Marker, if we need to download the package.
		download = True

		# Add shortcut for cache.
		cache = self.repo.cache

		cache_filename = "packages/%s" % os.path.basename(self.filename)

		# Check if file already exists in cache.
		if cache.exists(cache_filename):
			# If the file does already exist, we check if the hash1 matches.
			if cache.verify(cache_filename, self.hash1):
				# We already got the right file. Skip download.
				download = False
			else:
				# The file in cache has a wrong hash. Remove it and repeat download.
				cache.remove(cache_filename)

		if download:
			# Make sure filename is of type string (and not unicode)
			filename = str(self.filename)

			# Get a package grabber and add mirror download capabilities to it.
			grabber = pakfire.downloader.PackageDownloader(
				text=text + os.path.basename(filename),
			)
			grabber = self.repo.mirrors.group(grabber)

			i = grabber.urlopen(filename)

			# Open input and output files and download the file.
			o = cache.open(cache_filename, "w")

			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(buf)
				buf = i.read(BUFFER_SIZE)

			i.close()
			o.close()

			# Verify if the download was okay.
			if not cache.verify(cache_filename, self.hash1):
				raise Exception, "XXX this should never happen..."

		filename = os.path.join(cache.path, cache_filename)
		return BinaryPackage(self.pakfire, self.repo, filename)

# XXX maybe we can remove this later?
class InstalledPackage(DatabasePackage):
	type = "installed"

