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
import shutil
import tempfile
import urlgrabber

import logging
log = logging.getLogger("pakfire")

import base
import metadata

import pakfire.compress as compress
import pakfire.downloader as downloader
import pakfire.packages as packages
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class RepositoryDir(base.RepositoryFactory):
	def __init__(self, pakfire, name, description, path, key_id=None):
		base.RepositoryFactory.__init__(self, pakfire, name, description)

		# Path to files.
		self.path = path

		# The key that is used to sign all added packages.
		self.key_id = key_id

	def remove(self):
		self.index.clear()
		util.rm(self.path)

	@property
	def priority(self):
		"""
			The local repository has always a high priority.
		"""
		return 10

	@property
	def local(self):
		# Yes, this is local.
		return True

	def search_files(self, *paths):
		"""
			Search for possible package files in the paths.
		"""
		files = []

		for path in paths:
			if not os.path.exists(path):
				continue

			if os.path.isdir(path):
				for dir, subdirs, _files in os.walk(path):
					for file in sorted(_files):
						# Skip files that do not have the right extension
						if not file.endswith(".%s" % PACKAGE_EXTENSION):
							continue

						file = os.path.join(dir, file)
						files.append(file)

			elif os.path.isfile(path) and path.endswith(".%s" % PACKAGE_EXTENSION):
				files.append(path)

		return files

	def download_package(self, url):
		grabber = downloader.PackageDownloader(self.pakfire)

		tmpfile = None
		try:
			tmpfile = tempfile.NamedTemporaryFile(mode="wb", delete=False)
			tmpfile.close()

			basename = os.path.basename(url)
			grabber.urlgrab(url, filename=tmpfile.name, text=basename)

			# Add the package to the repository.
			self.add_package(tmpfile.name)
		finally:
			# Delete the temporary file afterwards.
			# Ignore any errors.
			if tmpfile:
				try:
					os.unlink(tmpfile.name)
				except:
					pass

	def add_packages(self, files):
		# Search for possible package files in the paths.
		files = self.search_files(*files)

		# Give up if there are no files to process.
		if not files:
			return

		# Create progress bar.
		pb = util.make_progress(_("%s: Adding packages...") % self.name, len(files))
		i = 0

		for file in files:
			if pb:
				i += 1
				pb.update(i)

			# Add the package to the repository.
			self.add_package(file, optimize_index=False)

		# Optimize the index.
		self.optimize_index()

		if pb:
			pb.finish()

		# Optimize the index.
		self.index.optimize()

	def add_package(self, filename, optimize_index=True, check_uuids=False):
		repo_filename = os.path.join(self.path, os.path.basename(filename))

		# Check if the package needs to be copied.
		needs_copy = True

		if os.path.exists(repo_filename):
			pkg2 = packages.open(self.pakfire, self, repo_filename)

			if check_uuids:
				pkg1 = packages.open(self.pakfire, None, filename)

				# Package file does already exist, but the UUID don't match.
				# Copy the package file and then re-open it.
				if pkg1.uuid == pkg2.uuid:
					needs_copy = False
			else:
				needs_copy = False

		# Copy the package file
		if needs_copy:
			if not os.path.exists(self.path):
				os.makedirs(self.path)

			# Copy the file.
			try:
				os.link(filename, repo_filename)
			except OSError:
				shutil.copy2(filename, repo_filename)

			# Re-open the package.
			pkg2 = packages.open(self.pakfire, self, repo_filename)

			# The package needs to be signed.
			if self.key_id:
				pkg2.sign(self.key_id)

		# Add package to the index.
		self.index.add_package(pkg2)

		if optimize_index:
			self.optimize_index()

	def optimize_index(self):
		"""
			Optimize the index.
		"""
		self.index.optimize()

	def save(self, path=None, algo="xz"):
		"""
			This function saves the database and metadata to path so it can
			be exported to a remote repository.
		"""
		if not path:
			path = self.path

		# Create filenames
		metapath = os.path.join(path, METADATA_DOWNLOAD_PATH)
		db_path = os.path.join(metapath, METADATA_DATABASE_FILE)
		md_path = os.path.join(metapath, METADATA_DOWNLOAD_FILE)

		# Remove all pre-existing metadata.
		if os.path.exists(metapath):
			util.rm(metapath)

		# Create directory for metdadata.
		os.makedirs(metapath)

		# Save the database to path and get the filename.
		self.index.write(db_path)

		# Make a reference to the database file that it will get a unique name
		# so we won't get into any trouble with caching proxies.
		db_hash = util.calc_hash1(db_path)

		db_path2 = os.path.join(os.path.dirname(db_path),
			"%s-%s" % (db_hash, os.path.basename(db_path)))

		# Compress the database.
		if algo:
			# Open input file and get filesize of input file.
			f = open(db_path)
			filesize = os.path.getsize(db_path)

			# Make a nice progress bar.
			p = util.make_progress(_("Compressing database..."), filesize)

			# Create compressing file handler.
			c = compress.compressobj(db_path2)

			try:
				size = 0
				while True:
					buf = f.read(BUFFER_SIZE)
					if not buf:
						break

					if p:
						size += len(buf)
						p.update(size)

					c.write(buf)
			except:
				# XXX catch compression errors
				raise

			finally:
				f.close()
				c.close()
				p.finish()

				# Remove old database.
				os.unlink(db_path)

		else:
			shutil.move(db_path, db_path2)

		# Create a new metadata object and add out information to it.
		md = metadata.Metadata(self.pakfire)

		# Save name of the hashed database to the metadata.
		md.database = os.path.basename(db_path2)
		md.database_hash1 = db_hash
		md.database_compression = algo

		# Save metdata to repository.
		md.save(md_path)


class RepositoryBuild(RepositoryDir):
	def __init__(self, pakfire):
		# XXX it is also hardcoded
		path = pakfire.config.get(None, "local_build_repo_path", "/var/lib/pakfire/local")
		#path = os.path.join(path, pakfire.distro.sname)
		assert path

		RepositoryDir.__init__(self, pakfire, "build", "Locally built packages", path)

	def open(self):
		# Find all files in the repository dir.
		files = self.search_files(self.path)

		# Create progress bar.
		pb = util.make_progress(_("%s: Reading packages...") % self.name, len(files))
		i = 0

		# Add all files to the index.
		for file in files:
			if pb:
				i += 1
				pb.update(i)

			pkg = packages.open(self.pakfire, self, file)
			self.index.add_package(pkg)

		if pb:
			pb.finish()

		# Mark repo as open.
		self.opened = True

	def close(self):
		# Wipe the index.
		self.index.clear()

		# Mark repository as not being open.
		self.opened = False

	@property
	def local(self):
		"""
			Yes, this is local.
		"""
		return True

	@property
	def priority(self):
		return 20000
