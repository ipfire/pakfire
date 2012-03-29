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

import logging
log = logging.getLogger("pakfire")

import base
import metadata

import pakfire.compress as compress
import pakfire.packages as packages
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class RepositoryDir(base.RepositoryFactory):
	def __init__(self, pakfire, name, description, path, type="binary", key_id=None):
		base.RepositoryFactory.__init__(self, pakfire, name, description)

		# Path to files.
		self.path = path

		# Save type.
		assert type in ("binary", "source",)
		self.type = type

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

	def add_packages(self, *paths):
		# Search for possible package files in the paths.
		files = self.search_files(*paths)

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

			# Open the package file we want to add.
			pkg = packages.open(self.pakfire, self, file)

			# Find all packages with the given type and skip those of
			# the other type.
			if not pkg.type == self.type:
				continue

			# Compute the local path.
			repo_filename = os.path.join(self.path, os.path.basename(pkg.filename))
			pkg2 = None

			# If the file is already located in the repository, we do not need to
			# copy it.
			if not pkg.filename == repo_filename:
				need_copy = True

				# Check if the file is already in the repository.
				if os.path.exists(repo_filename):
					# Open it for comparison.
					pkg2 = packages.open(self.pakfire, self, repo_filename)

					if pkg.uuid == pkg2.uuid:
						need_copy = False

				# If a copy is still needed, we do it.
				if need_copy:
					# Create the directory.
					repo_dirname = os.path.dirname(repo_filename)
					if not os.path.exists(repo_dirname):
						os.makedirs(repo_dirname)

					# Try to use a hard link if possible, if we cannot do that we simply
					# copy the file.
					try:
						os.link(pkg.filename, repo_filename)
					except OSError:
						shutil.copy2(pkg.filename, repo_filename)

			# Reopen the new package file (in case it needs to be changed).
			if pkg2:
				pkg = pkg2
			else:
				pkg = packages.open(self.pakfire, self, repo_filename)

			# Sign all packages.
			if self.key_id:
				pkg.sign(self.key_id)

			# Add the package to the index.
			self.index.add_package(pkg)

		if pb:
			pb.finish()

		# Optimize the index.
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

	def update(self, force=False, offline=False):
		# If force is not given, but there are no files in the repository,
		# we force an update anyway.
		if not force:
			force = len(self) == 0

		if force:
			# Wipe the index.
			self.index.clear()

			# Find all files in the repository dir.
			files = self.search_files(self.path)

			# Create progress bar.
			pb = util.make_progress(_("%s: Adding packages...") % self.name, len(files))
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

	@property
	def local(self):
		"""
			Yes, this is local.
		"""
		return True

	@property
	def priority(self):
		return 20000
