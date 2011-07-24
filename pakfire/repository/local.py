#!/usr/bin/python

import logging
import os
import shutil

import base
import index
import metadata

import pakfire.compress as compress
import pakfire.packages as packages
import pakfire.util as util

from pakfire.constants import *

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

	def collect_packages(self, *args, **kwargs):
		"""
			Proxy function to add packages to the index.
		"""

		for pkg in self.index.collect_packages(*args, **kwargs):
			# The path of the package in the repository
			repo_filename = os.path.join(self.path, os.path.basename(pkg.filename))

			# Do we need to copy the package files?
			copy = True

			# Check, if the package does already exists and check if the
			# files are really equal.
			if os.path.exists(repo_filename):
				pkg_exists = packages.open(self.pakfire, self, repo_filename)

				# Check UUID at first (faster) and check the file hash to be
				# absolutely sure.
				if pkg.uuid == pkg_exists.uuid and pkg.hash1 == pkg_exists.hash1:
					# Do not copy the file if it is already okay.
					copy = False

				# Otherwise, unlink the existing file and replace it with the
				# new one.
				else:
					os.unlink(repo_filename)

				del pkg_exists

			if copy:
				logging.debug("Copying package '%s' to repository." % pkg)
				repo_dirname = os.path.dirname(repo_filename)
				if not os.path.exists(repo_dirname):
					os.makedirs(repo_dirname)

				# Try to use a hard link if possible, if we cannot do that we simply
				# copy the file.
				try:
					os.link(pkg.filename, repo_filename)
				except OSError:
					shutil.copy2(pkg.filename, repo_filename)

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

		if not os.path.exists(metapath):
			os.makedirs(metapath)

		else:
			# If a database is present, we remove it because we want to start
			# with a clean environment.
			if os.path.exists(db_path):
				os.unlink(db_path)

		# Save the database to path and get the filename.
		self.index.write(db_path)

		# Make a reference to the database file that it will get a unique name
		# so we won't get into any trouble with caching proxies.
		db_hash = util.calc_hash1(db_path)

		db_path2 = os.path.join(os.path.dirname(db_path),
			"%s-%s" % (db_hash, os.path.basename(db_path)))

		# Compress the database.
		if algo:
			compress.compress(db_path, algo=algo, progress=True)

		if not os.path.exists(db_path2):
			shutil.move(db_path, db_path2)
		else:
			os.unlink(db_path)

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
