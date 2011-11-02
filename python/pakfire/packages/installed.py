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

import os

import pakfire.downloader
import pakfire.filelist

from base import Package
from file import BinaryPackage

import pakfire.util as util
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
	def groups(self):
		groups = self.metadata.get("groups", "")

		if groups:
			return groups.split()

		return []

	@property
	def build_date(self):
		return self.metadata.get("build_date")

	@property
	def build_time(self):
		build_time = self.metadata.get("build_time", 0)

		try:
			return int(build_time)
		except TypeError:
			return 0

	@property
	def build_host(self):
		return self.metadata.get("build_host")

	@property
	def build_id(self):
		return self.metadata.get("build_id")

	@property
	def vendor(self):
		return self.metadata.get("vendor")

	@property
	def uuid(self):
		return self.metadata.get("uuid")

	@property
	def size(self):
		return self.metadata.get("size", 0)

	@property
	def inst_size(self):
		# XXX to be done
		return 0

	@property
	def provides(self):
		return self.metadata.get("provides", "").split()

	@property
	def requires(self):
		return self.metadata.get("requires", "").split()

	@property
	def conflicts(self):
		return self.metadata.get("conflicts", "").split()

	@property
	def obsoletes(self):
		return self.metadata.get("obsoletes", "").split()

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
		filelist = []

		c = self.db.cursor()
		c.execute("SELECT id FROM files WHERE pkg = ?", (self.id,))

		for id in c:
			file = pakfire.filelist.FileDatabase(self.pakfire, self.db, id[0])
			filelist.append(file)

		return filelist

	@property
	def configfiles(self):
		ret = []

		for file in self.filelist:
			if not file.is_config():
				continue

			ret.append(file)

		return ret

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

		# XXX a bit hacky, but InstalledRepository has no cache.
		if self.repo.name == "installed":
			return self

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

	def cleanup(self, message, prefix):
		c = self.db.cursor()

		# Get all files, that are in this package and check for all of
		# them if they need to be removed.
		files = self.filelist

		# Fetch the whole filelist of the system from the database and create
		# a diff. Exclude files from this package - of course.
		c.execute("SELECT DISTINCT name FROM files WHERE pkg != ?", (self.id,))

		installed_files = set()
		for row in c:
			installed_files.add(row["name"])
		c.close()

		# List with files to be removed.
		remove_files = []

		for f in files:
			if f.name in installed_files:
				continue

			remove_files.append(f)

		self._remove_files(remove_files, message, prefix)


# XXX maybe we can remove this later?
class InstalledPackage(DatabasePackage):
	type = "installed"

