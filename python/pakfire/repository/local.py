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
import index
import metadata

import pakfire.compress as compress
import pakfire.packages as packages
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class RepositoryDir(base.RepositoryFactory):
	def __init__(self, pakfire, name, description, path, type="binary"):
		base.RepositoryFactory.__init__(self, pakfire, name, description)

		# Path to files.
		self.path = path

		# Save type.
		assert type in ("binary", "source",)
		self.type = type

		# Create index
		self.index = index.IndexDir(self.pakfire, self)

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

	def collect_packages(self, *args, **kwargs):
		"""
			Proxy function to add packages to the index.
		"""

		for pkg in self.index.collect_packages(*args, **kwargs):
			# The path of the package in the repository
			repo_filename = os.path.join(self.path, os.path.basename(pkg.filename))

			# Check, if the package does already exists and check if the
			# files are really equal.
			if os.path.exists(repo_filename):
				pkg_exists = packages.open(self.pakfire, self, repo_filename)

				# Check UUID to see if the file needs to be copied.
				if pkg.uuid == pkg_exists.uuid:
					continue

			log.debug("Copying package '%s' to repository." % pkg)
			repo_dirname = os.path.dirname(repo_filename)
			if not os.path.exists(repo_dirname):
				os.makedirs(repo_dirname)

			# Try to use a hard link if possible, if we cannot do that we simply
			# copy the file.
			try:
				os.link(pkg.filename, repo_filename)
			except OSError:
				shutil.copy2(pkg.filename, repo_filename)

	def sign(self, key_id):
		"""
			Sign all packages with the given key.
		"""
		# Create progressbar.
		pb = util.make_progress(_("Signing packages..."), len(self), eta=True)
		i = 0

		# Create a new index (because package checksums will change).
		for pkg in self:
			if pb:
				i += 1
				pb.update(i)

			# Create the full path to the file.
			filename = os.path.join(self.path, pkg.filename)
			pkg = packages.open(self.pakfire, self, filename)

			# Sign the package.
			pkg.sign(key_id)

		if pb:
			pb.finish()

		# Recreate the index because file checksums may have changed.
		self.index.update(force=True)

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
		md = metadata.Metadata(self.pakfire, self)

		# Save name of the hashed database to the metadata.
		md.database = os.path.basename(db_path2)
		md.database_hash1 = db_hash
		md.database_compression = algo

		# Save metdata to repository.
		md.save(md_path)


class RepositoryBuild(RepositoryDir):
	def __init__(self, pakfire):
		# XXX need to add distro information to this path
		path = pakfire.config.get("local_build_repo_path")

		# Create path if it does not exist.
		if not os.path.exists(path):
			os.makedirs(path)

		RepositoryDir.__init__(self, pakfire, "build", "Locally built packages", path)

	@property
	def local(self):
		"""
			Yes, this is local.
		"""
		return True

	@property
	def priority(self):
		return 20000


class RepositoryLocal(base.RepositoryFactory):
	def __init__(self, pakfire):
		base.RepositoryFactory.__init__(self, pakfire, "@system", "Local repository")

		self.index = index.IndexLocal(self.pakfire, self)

		# Tell the solver, that these are the installed packages.
		self.pool.set_installed(self.solver_repo)

	@property
	def priority(self):
		"""
			The local repository has always a high priority.
		"""
		return 10

	def add_package(self, pkg):
		# Add package to the database.
		self.index.db.add_package(pkg)

		self.index.add_package(pkg)

	def rem_package(self, pkg):
		# Remove package from the database.
		self.index.rem_package(pkg)

	@property
	def filelist(self):
		return self.index.filelist
