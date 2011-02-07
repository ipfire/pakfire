#!/usr/bin/python

import hashlib
import time

import util

from base import Package


# XXX maybe this gets renamed to "DatabasePackage" or something similar.

class InstalledPackage(Package):
	type = "installed"

	def __init__(self, pakfire, db, data):
		Package.__init__(self, pakfire, pakfire.repos.local)

		self.db = db

		self._data = {}

		for key in data.keys():
			self._data[key] = data[key]

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.friendly_name)

	@property
	def metadata(self):
		return self._data

	@property
	def id(self):
		id = self.metadata.get("id")
		if not id:
			id = 0

		return id

	@property
	def name(self):
		return self.metadata.get("name")

	@property
	def version(self):
		return self.metadata.get("version")

	@property
	def release(self):
		return self.metadata.get("release")

	@property
	def epoch(self):
		epoch = self.metadata.get("epoch", 0)

		return int(epoch)

	@property
	def arch(self):
		return self.metadata.get("arch")

	@property
	def maintainer(self):
		return self.metadata.get("maintainer")

	@property
	def license(self):
		return self.metadata.get("license")

	@property
	def summary(self):
		return self.metadata.get("summary")

	@property
	def description(self):
		return self.metadata.get("description")

	@property
	def group(self):
		return self.metadata.get("group")

	@property
	def build_data(self):
		return self.metadata.get("build_data")

	@property
	def build_host(self):
		return self.metadata.get("build_host")

	@property
	def build_id(self):
		return self.metadata.get("build_id")

	@property
	def provides(self):
		provides = self.metadata.get("provides")
		
		if provides:
			return provides.split()

		return []

	@property
	def requires(self):
		requires = self.metadata.get("requires")
		
		if requires:
			return requires.split()

		return []

	@property
	def conflicts(self):
		conflicts = self.metadata.get("conflicts")

		if conflicts:
			return conflicts.split()

		return []

	@property
	def filelist(self):
		c = self.db.cursor()
		c.execute("SELECT name FROM files WHERE pkg = '%s'" % self.id) # XXX?

		for f in c:
			yield f["name"]

		c.close()

	## database methods

	def set_installed(self, installed):
		c = self.db.cursor()
		c.execute("UPDATE packages SET installed = ? WHERE id = ?", (installed, self.id))
		c.close()

	def add_file(self, filename, type=None, size=None, hash1=None, **kwargs):
		if not hash1:
			hash1 = util.calc_hash1(filename)

		if size is None:
			size = os.path.getsize(filename)

		c = self.db.cursor()
		c.execute("INSERT INTO files(name, pkg, size, type, hash1, installed) \
			VALUES(?, ?, ?, ?, ?, ?)",
			(filename, self.id, size, type, hash1, time.time()))
		c.close()

