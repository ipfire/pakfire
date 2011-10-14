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

import logging
import os
import random
import shutil
import sqlite3
import time

import pakfire.packages as packages

from pakfire.constants import *
from pakfire.i18n import _

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

	def migrate(self):
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

			# In the case, the database was not existant, it is
			# filled with content. In case it has been there
			# we call the migrate method to update it if neccessary.
			if database_exists:
				self.migrate()
			else:
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

		# Cache format number.
		self.__format = None

		Database.__init__(self, pakfire, filename)

		# Check if we actually can open the database.
		if not self.format in DATABASE_FORMATS_SUPPORTED:
			raise DatabaseFormatError, _("The format of the database is not supported by this version of pakfire.")

	def __len__(self):
		count = 0

		c = self.cursor()
		c.execute("SELECT COUNT(*) AS count FROM packages")
		for row in c:
			count = row["count"]
		c.close()

		return count

	@property
	def format(self):
		if self.__format is None:
			c = self.cursor()

			c.execute("SELECT val FROM settings WHERE key = 'version' LIMIT 1")
			for row in c:
				try:
					self.__format = int(row["val"])
					break
				except ValueError:
					pass

			c.close()

		return self.__format

	def create(self):
		c = self.cursor()
		c.executescript("""
			CREATE TABLE settings(
				key			TEXT,
				val			TEXT
			);
			INSERT INTO settings(key, val) VALUES('version', '%s');

			CREATE TABLE files(
				id		INTEGER PRIMARY KEY,
				name		TEXT,
				pkg		INTEGER,
				size		INTEGER,
				type		INTEGER,
				config		INTEGER,
				mode		INTEGER,
				user		TEXT,
				`group`		TEXT,
				hash1		TEXT,
				mtime		INTEGER
			);

			CREATE TABLE packages(
				id		INTEGER PRIMARY KEY,
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
				vendor		TEXT,
				build_id	TEXT,
				build_host	TEXT,
				build_date	TEXT,
				build_time	INTEGER,
				installed	INT,
				reason		TEXT,
				repository	TEXT
			);

			CREATE TABLE scriptlets(
				id			INTEGER PRIMARY KEY,
				pkg			INTEGER,
				action		TEXT,
				scriptlet	TEXT
			);

			CREATE TABLE triggers(
				id			INTEGER PRIMARY KEY,
				pkg			INTEGER,
				dependency	TEXT,
				scriptlet	TEXT
			);
		""" % DATABASE_FORMAT)
		# XXX add some indexes here
		self.commit()
		c.close()

	def migrate(self):
		# If we have already the latest version, there is nothing to do.
		if self.format == DATABASE_FORMAT:
			return

		logging.info(_("Migrating database from format %s to %s.") % (self.format, DATABASE_FORMAT))

		# Get a database cursor.
		c = self.cursor()

		# 1) The vendor column was added.
		if self.format < 1:
			c.execute("ALTER TABLE packages ADD COLUMN vendor TEXT AFTER uuid")

		if self.format < 2:
			c.execute("ALTER TABLE files ADD COLUMN `config` INTEGER")
			c.execute("ALTER TABLE files ADD COLUMN `mode` INTEGER")
			c.execute("ALTER TABLE files ADD COLUMN `user` TEXT")
			c.execute("ALTER TABLE files ADD COLUMN `group` TEXT")
			c.execute("ALTER TABLE files ADD COLUMN `mtime` INTEGER")

		# In the end, we can easily update the version of the database.
		c.execute("UPDATE settings SET val = ? WHERE key = 'version'", (DATABASE_FORMAT,))
		self.__format = DATABASE_FORMAT

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
					vendor,
					build_id,
					build_host,
					build_date,
					build_time,
					installed,
					repository,
					reason
				) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
					pkg.vendor or "",
					pkg.build_id,
					pkg.build_host,
					pkg.build_date,
					pkg.build_time,
					time.time(),
					pkg.repo.name,
					reason or "",
				)
			)

			pkg_id = c.lastrowid

			c.executemany("INSERT INTO files(`name`, `pkg`, `size`, `config`, `type`, `hash1`, `mode`, `user`, `group`, `mtime`)"
					" VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
				((f.name, pkg_id, f.size, f.is_config(), f.type, f.hash1, f.mode, f.user, f.group, f.mtime) for f in pkg.filelist))

		except:
			raise

		else:
			self.commit()

		c.close()

	def rem_package(self, pkg):
		logging.debug("Removing package from database: %s" % pkg.friendly_name)

		assert pkg.uuid

		# Get the ID of the package in the database.
		c = self.cursor()
		#c.execute("SELECT id FROM packages WHERE uuid = ? LIMIT 1", (pkg.uuid,))
		c.execute("SELECT id FROM packages WHERE name = ? AND epoch = ? AND version = ?"
			" AND release = ? LIMIT 1", (pkg.name, pkg.epoch, pkg.version, pkg.release,))

		id = None
		for row in c:
			id = row["id"]
			break
		assert id

		# First, delete all files from the database and then delete the pkg itself.
		c.execute("DELETE FROM files WHERE pkg = ?", (id,))
		c.execute("DELETE FROM packages WHERE id = ?", (id,))

		c.close()
		self.commit()

	def get_package_by_id(self, id):
		c = self.cursor()
		c.execute("SELECT * FROM packages WHERE id = ?", (id,))

		try:
			for row in c:
				return packages.DatabasePackage(self.pakfire, self.repo, self, row)

		finally:
			c.close()

	@property
	def packages(self):
		c = self.cursor()

		c.execute("SELECT * FROM packages ORDER BY name")

		for row in c:
			yield packages.DatabasePackage(self.pakfire, self.repo, self, row)

		c.close()

	def get_package_from_solv(self, solv_pkg):
		c = self.cursor()
		c.execute("SELECT * FROM packages WHERE uuid = ? LIMIT 1", (solv_pkg.uuid,))

		try:
			for row in c:
				return packages.DatabasePackage(self.pakfire, self.repo, self, row)

		finally:
			c.close()
