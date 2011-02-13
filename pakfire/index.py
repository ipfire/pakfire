#!/usr/bin/python

import logging
import os

import database
import packages

from constants import *

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


class DirectoryIndex(Index):
	def __init__(self, pakfire, repo, path):
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
	def __init__(self, pakfire, repo, db):
		self.db = db

		Index.__init__(self, pakfire, repo)

	def update(self, force=False):
		"""
			Nothing to do here.
		"""
		pass

	def get_all_by_name(self, name):
		c = self.db.cursor()
		c.execute("SELECT * FROM packages WHERE name = ?", name)

		for pkg in c:
			yield package.DatabasePackage(self.pakfire, self.db, pkg)

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
			yield packages.DatabasePackage(self.pakfire, self.db, pkg)

		c.close()


# XXX maybe this can be removed later?
class InstalledIndex(DatabaseIndex):
	pass

