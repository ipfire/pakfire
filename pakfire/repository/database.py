#!/usr/bin/python

import logging
import os
import random
import shutil
import sqlite3
import time

import pakfire.packages as packages

from pakfire.constants import *

class Cursor(sqlite3.Cursor):
	def execute(self, *args, **kwargs):
		# For debugging of SQL queries.
		#print args, kwargs

		return sqlite3.Cursor.execute(self, *args, **kwargs)


class Database(object):
	def __init__(self, pakfire, filename):
		self.pakfire = pakfire
		self.filename = filename

		self._db = None

	def __del__(self):
		if self._db:
			self._db.close()
			self._db = None

	def create(self):
		pass

	def open(self):
		if self._db is None:
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
		self.__del__()

	def commit(self):
		self.open()
		self._db.commit()

	def cursor(self):
		self.open()
		return self._db.cursor(Cursor)

	def executescript(self, *args, **kwargs):
		self.open()
		return self._db.executescript(*args, **kwargs)


class DatabaseLocal(Database):
	def __init__(self, pakfire, repo):
		self.repo = repo

		# Generate filename for package database
		filename = os.path.join(pakfire.path, PACKAGES_DB)

		Database.__init__(self, pakfire, filename)

	def __len__(self):
		count = 0

		c = self.cursor()
		c.execute("SELECT COUNT(*) AS count FROM packages")
		for row in c:
			count = row["count"]
		c.close()

		return count

	def create(self):
		c = self.cursor()
		c.executescript("""
			CREATE TABLE settings(
				key			TEXT,
				val			TEXT
			);
			INSERT INTO settings(key, val) VALUES('version', '0');

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
				groups		TEXT,
				filename	TEXT,
				size		INTEGER,
				hash1		TEXT,
				provides	TEXT,
				requires	TEXT,
				conflicts	TEXT,
				obsoletes	TEXT,
				license		TEXT,
				summary		TEXT,
				description	TEXT,
				uuid		TEXT,
				build_id	TEXT,
				build_host	TEXT,
				build_date	TEXT,
				build_time	INTEGER,
				installed	INT,
				reason		TEXT,
				repository	TEXT,
				scriptlet	TEXT,
				triggers	TEXT
			);
		""")
		# XXX add some indexes here
		self.commit()
		c.close()

	def add_package(self, pkg, reason=None):
		logging.debug("Adding package to database: %s" % pkg.friendly_name)

		c = self.cursor()

		try:
			c.execute("""
				INSERT INTO packages(
					name,
					epoch,
					version,
					release,
					arch,
					groups,
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
					uuid,
					build_id,
					build_host,
					build_date,
					build_time,
					installed,
					repository,
					reason,
					scriptlet,
					triggers
				) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
				(
					pkg.name,
					pkg.epoch,
					pkg.version,
					pkg.release,
					pkg.arch,
					" ".join(pkg.groups),
					pkg.filename,
					pkg.size,
					pkg.hash1,
					" ".join(pkg.provides),
					" ".join(pkg.requires),
					" ".join(pkg.conflicts),
					" ".join(pkg.obsoletes),
					pkg.license,
					pkg.summary,
					pkg.description,
					pkg.uuid,
					pkg.build_id,
					pkg.build_host,
					pkg.build_date,
					pkg.build_time,
					time.time(),
					pkg.repo.name,
					reason or "",
					pkg.scriptlet,
					" ".join(pkg.triggers)
				)
			)

			pkg_id = c.lastrowid

			c.executemany("INSERT INTO files(name, pkg) VALUES(?, ?)",
				((file, pkg_id) for file in pkg.filelist))

		except:
			raise

		else:
			self.commit()

		c.close()

	@property
	def packages(self):
		c = self.cursor()

		c.execute("SELECT * FROM packages ORDER BY name")

		for row in c:
			yield packages.DatabasePackage(self.pakfire, self.repo, self, row)

		c.close()
