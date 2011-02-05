#!/usr/bin/python

import logging
import os
import sqlite3

import packages

class Database(object):
	def __init__(self, filename):
		self.filename = filename
		self._db = None

		self.open()

	def __del__(self):
		if self._db:
			self._db.commit()
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


class LocalPackageDatabase(Database):
	def create(self):
		c = self.cursor()

		c.executescript("""
			CREATE TABLE files(
				name		TEXT,
				pkg			INTEGER,
				size		INTEGER,
				type		INTEGER,
				hash1		TEXT,
				installed	INTEGER,
				changed		INTEGER
			);

			CREATE TABLE packages(
				id			INTEGER PRIMARY KEY,
				name		TEXT,
				epoch		INTEGER,
				version		TEXT,
				release		TEXT,
				installed	INTEGER,
				reason		TEXT,
				repository	TEXT,
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

	def add_package(self, pkg, installed=True):
		c = self.cursor()

		c.execute("INSERT INTO packages(name, epoch, version, release, installed, \
			provides, requires, build_id, build_host, build_date) \
			VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
			pkg.name,
			pkg.epoch,
			pkg.version,
			pkg.release,
			int(installed),
			" ".join(pkg.provides),
			" ".join(pkg.requires),
			pkg.build_id,
			pkg.build_host,
			pkg.build_date
		))

		#c.close()

		# Get the id from the package
		#c = self.cursor()
		#c.execute("SELECT * FROM packages WHERE build_id = ? LIMIT 1", (pkg.build_id))
		c.execute("SELECT * FROM packages WHERE name = ? AND version = ? AND \
			release = ? AND epoch = ? LIMIT 1", (pkg.name, pkg.version, pkg.release, pkg.epoch))

		ret = None
		for pkg in c:
			ret = packages.InstalledPackage(self, pkg)
			break

		assert ret
		c.close()

		return ret

