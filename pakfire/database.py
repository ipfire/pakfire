#!/usr/bin/python

import logging
import os
import sqlite3
import time

import packages

from constants import *

class Database(object):
	def __init__(self, pakfire, filename):
		self.pakfire = pakfire
		self.filename = filename
		self._db = None

		self.open()

	def __del__(self):
		if self._db:
			#self._db.commit()
			self._db.close()

	def create(self):
		pass

	def open(self):
		if not self._db:
			logging.debug("Open database %s" % self.filename)

			dirname = os.path.dirname(self.filename)
			if not os.path.exists(dirname):
				os.makedirs(dirname)

			database_exists = os.path.exists(self.filename)

			# Make a connection to the database.
			self._db = sqlite3.connect(self.filename)
			self._db.row_factory = sqlite3.Row

			# Create the database if it was not there, yet.
			if not database_exists:
				self.create()

	def close(self):
		self._db.close()

	def commit(self):
		self._db.commit()

	def cursor(self):
		return self._db.cursor()


class PackageDatabase(Database):
	def create(self):
		c = self.cursor()

		c.executescript("""
			CREATE TABLE files(
				name		TEXT,
				pkg			INTEGER,
				size		INTEGER,
				type		INTEGER,
				hash1		TEXT
			);

			CREATE TABLE packages(
				id			INTEGER PRIMARY KEY,
				name		TEXT,
				epoch		INTEGER,
				version		TEXT,
				release		TEXT,
				arch		TEXT,
				filename	TEXT,
				size		INT,
				hash1		TEXT,
				provides	TEXT,
				requires	TEXT,
				conflicts	TEXT,
				obsoletes	TEXT,
				license		TEXT,
				summary		TEXT,
				description	TEXT,
				build_id	TEXT,
				build_host	TEXT,
				build_date	INT
			);
		""")
		# XXX add some indexes here

		self.commit()
		c.close()

	def list_packages(self):
		c = self.cursor()
		c.execute("SELECT DISTINCT name FROM packages ORDER BY name")

		for pkg in c:
			yield pkg["name"]

		c.close()

	def package_exists(self, pkg):
		return not self.get_id_by_pkg(pkg) is None

	def get_id_by_pkg(self, pkg):
		c = self.cursor()

		c.execute("SELECT id FROM packages WHERE name = ? AND version = ? AND \
			release = ? AND epoch = ? LIMIT 1", (pkg.name, pkg.version, pkg.release, pkg.epoch))

		ret = None
		for i in c:
			ret = i["id"]
			break

		c.close()

		return ret

	def add_package(self, pkg):
		raise NotImplementedError


class RemotePackageDatabase(PackageDatabase):
	def add_package(self, pkg, reason=None):
		if self.package_exists(pkg):
			logging.debug("Skipping package which already exists in database: %s" % pkg.friendly_name)
			return

		logging.debug("Adding package to database: %s" % pkg.friendly_name)

		filename = ""
		if pkg.repo.local:
			# Get the path relatively to the repository.
			filename = pkg.filename[len(pkg.repo.path):]
			# Strip leading / if any.
			if filename.startswith("/"):
				filename = filename[1:]

		c = self.cursor()
		c.execute("""
			INSERT INTO packages(
				name,
				epoch,
				version,
				release,
				arch,
				filename,
				size,
				hash1,
				provides,
				requires,
				conflicts,
				obsoletes,
				license,
				summary,
				description,
				build_id,
				build_host,
				build_date
			) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
			(
				pkg.name,
				pkg.epoch,
				pkg.version,
				pkg.release,
				pkg.arch,
				filename,
				pkg.size,
				pkg.hash1,
				" ".join(pkg.provides),
				" ".join(pkg.requires),
				" ".join(pkg.conflicts),
				" ".join(pkg.obsoletes),
				pkg.license,
				pkg.summary,
				pkg.description,
				pkg.build_id,
				pkg.build_host,
				pkg.build_date
			)
		)
		self.commit()
		c.close()

		pkg_id = self.get_id_by_pkg(pkg)

		c = self.cursor()
		for file in pkg.filelist:
			c.execute("INSERT INTO files(name, pkg) VALUES(?, ?)", (file, pkg_id))

		self.commit()
		c.close()

		return pkg_id


class LocalPackageDatabase(RemotePackageDatabase):
	def __init__(self, pakfire):
		# Generate filename for package database
		filename = os.path.join(pakfire.path, PACKAGES_DB)

		RemotePackageDatabase.__init__(self, pakfire, filename)

	def create(self):
		RemotePackageDatabase.create(self)

		# Alter the database layout to store additional local information.
		logging.debug("Altering database table for local information.")
		c = self.cursor()
		c.executescript("""
			ALTER TABLE packages ADD COLUMN installed INT;
			ALTER TABLE packages ADD COLUMN reason TEXT;
			ALTER TABLE packages ADD COLUMN repository TEXT;
			ALTER TABLE packages ADD COLUMN scriptlet TEXT;
			ALTER TABLE packages ADD COLUMN triggers TEXT;
		""")
		self.commit()
		c.close()

	def add_package(self, pkg, reason=None):
		# Insert all the information to the database we have in the remote database
		pkg_id = RemotePackageDatabase.add_package(self, pkg)

		# then: add some more information
		c = self.cursor()

		# Save timestamp when the package was installed.
		c.execute("UPDATE packages SET installed = ? WHERE id = ?", (time.time(), pkg_id))

		# Add repository information.
		c.execute("UPDATE packages SET repository = ? WHERE id = ?", (pkg.repo.name, pkg_id))

		# Save reason of installation (if any).
		if reason:
			c.execute("UPDATE packages SET reason = ? WHERE id = ?", (reason, pkg_id))

		# Update the filename information.
		c.execute("UPDATE packages SET filename = ? WHERE id = ?", (pkg.filename, pkg_id))

		# Add the scriptlet to database (needed to update or uninstall packages).
		c.execute("UPDATE packages SET scriptlet = ? WHERE id = ?", (pkg.scriptlet, pkg_id))

		# Add triggers to the database.
		triggers = " ".join(pkg.triggers)
		c.execute("UPDATE packages SET triggers = ? WHERE id = ?", (triggers, pkg_id))

		self.commit()
		c.close()
