#!/usr/bin/python

import logging
import os
import shutil

import pakfire.packages as packages

import index

from base import RepositoryFactory

from pakfire.constants import *

class LocalRepository(RepositoryFactory):
	def __init__(self, pakfire, name, description, path):
		RepositoryFactory.__init__(self, pakfire, name, description)

		# Save location of the repository and create it if not existant.
		self.path = path
		if not os.path.exists(self.path):
			os.makedirs(self.path)

		self.index = index.LocalIndex(self.pakfire, self)

	@property
	def local(self):
		# This is obviously local.
		return True

	@property
	def priority(self):
		"""
			The local repository has always a high priority.
		"""
		return 10

	def _collect_packages(self, path):
		logging.info("Collecting packages from %s." % path)

		for dir, subdirs, files in os.walk(path):
			for file in files:
				if not file.endswith(".%s" % PACKAGE_EXTENSION):
					continue

				file = os.path.join(dir, file)

				pkg = packages.BinaryPackage(self.pakfire, self, file)
				self._add_package(pkg)

	def _add_package(self, pkg):
		# XXX gets an instance of binary package and puts it into the
		# repo location if not done yet
		# then: the package gets added to the index

		if not isinstance(pkg, packages.BinaryPackage):
			raise Exception

		repo_filename = os.path.join(self.path, os.path.basename(pkg.filename))

		# Do we need to copy the package files?
		copy = True

		pkg_exists = None
		if os.path.exists(repo_filename):
			pkg_exists = packages.BinaryPackage(self.pakfire, self, repo_filename)

			# If package in the repo is equivalent to the given one, we can
			# skip any further processing.
			if pkg == pkg_exists:
				logging.debug("The package does already exist in this repo: %s" % pkg.friendly_name)
				copy = False

		if copy:
			logging.debug("Copying package '%s' to repository." % pkg.friendly_name)
			repo_dirname = os.path.dirname(repo_filename)
			if not os.path.exists(repo_dirname):
				os.makedirs(repo_dirname)

			# Try to use a hard link if possible, if we cannot do that we simply
			# copy the file.
			try:
				os.link(pkg.filename, repo_filename)
			except OSError:
				shutil.copy2(pkg.filename, repo_filename)

		# Create new package object, that is connected to this repository
		# and so we can do stuff.
		pkg = packages.BinaryPackage(self.pakfire, self, repo_filename)

		logging.info("Adding package '%s' to repository." % pkg.friendly_name)
		self.index.add_package(pkg)

	def save(self, path=None):
		"""
			Save the index information to path.
		"""
		self.index.save(path)


class LocalBuildRepository(LocalRepository):
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "build", "Locally built packages")

		self.path = self.pakfire.config.get("local_build_repo_path")
		if not os.path.exists(self.path):
			os.makedirs(self.path)

		self.index = index.DirectoryIndex(self.pakfire, self, self.path)

	@property
	def priority(self):
		return 20000
