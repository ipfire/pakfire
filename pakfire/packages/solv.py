#!/usr/bin/python

import re

import base
import binary

class SolvPackage(base.Package):
	def __init__(self, pakfire, solvable):
		base.Package.__init__(self, pakfire)

		# Save solvable object
		self.solvable = solvable

		self.__evr = None

	@property
	def uuid(self):
		return self.solvable.get_uuid()

	@property
	def hash1(self):
		return self.solvable.get_hash1()

	@property
	def name(self):
		return self.solvable.get_name()

	@property
	def evr(self):
		if self.__evr is None:
			m = re.match("([0-9]+\:)?([0-9A-Za-z\.]+)-?([0-9]+\.?[a-z0-9]+|[0-9]+)?",
				self.solvable.get_evr())

			if m:
				(e, v, r) = m.groups()

				if e:
					e = e.replace(":", "")
					e = int(e)

				self.__evr = (e, v, r)

		return self.__evr

	@property
	def epoch(self):
		return self.evr[0]

	@property
	def version(self):
		return self.evr[1]

	@property
	def release(self):
		return self.evr[2]

	@property
	def arch(self):
		return self.solvable.get_arch()

	@property
	def repo(self):
		repo_name = self.solvable.get_repo_name()

		return self.pakfire.repos.get_repo(repo_name)

	@property
	def summary(self):
		return self.solvable.get_summary()

	@property
	def description(self):
		return self.solvable.get_description()

	@property
	def groups(self):
		return self.solvable.get_groups().split()

	@property
	def license(self):
		return self.solvable.get_license()

	@property
	def maintainer(self):
		return self.solvable.get_maintainer()

	@property
	def url(self):
		return self.solvable.get_url()

	@property
	def size(self):
		return self.solvable.get_downloadsize()

	@property
	def uuid(self):
		return self.solvable.get_uuid()

	@property
	def build_host(self):
		return self.solvable.get_buildhost()

	@property
	def build_time(self):
		return self.solvable.get_buildtime()

	@property
	def build_id(self):
		return "XXX CURRENTLY NOT IMPLEMENTED"

	@property
	def provides(self):
		return self.solvable.get_provides()

	@property
	def requires(self):
		return self.solvable.get_requires()

	@property
	def obsoletes(self):
		return self.solvable.get_obsoletes()

	@property
	def conflicts(self):
		return self.solvable.get_conflicts()

	@property
	def filename(self):
		return self.solvable.get_filename()

	@property
	def is_in_cache(self):
		return self.repo.cache.exists("package/%s" % self.filename)

	def get_from_cache(self):
		filename = "packages/%s" % self.filename

		if self.repo.cache.exists(filename):
			return binary.BinaryPackage(self.pakfire, self.repo, self.repo.cache.abspath(filename))

	def download(self, text=""):
		self.repo.download(self.filename, text=text, hash1=self.hash1)

		return self.get_from_cache()
