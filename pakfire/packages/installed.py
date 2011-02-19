#!/usr/bin/python

from base import Package

class DatabasePackage(Package):
	type = "db"

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
		provides = self.metadata.get("provides", "").split()

		# Add autoprovides
		for prov in self._provides:
			if not prov in provides:
				provides.append(prov)

		return provides

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
			filename = f["name"]
			if not filename.startswith("/"):
				filename = "/%s" % filename

			yield filename

		c.close()


# XXX maybe we can remove this later?
class InstalledPackage(DatabasePackage):
	type = "installed"

