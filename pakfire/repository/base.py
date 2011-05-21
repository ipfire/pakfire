#!/usr/bin/python

import fnmatch
import glob
import logging
import re

class RepositoryFactory(object):
	def __init__(self, pakfire, name, description):
		self.pakfire = pakfire

		self.name, self.description = name, description

		# All repositories are enabled by default
		self.enabled = True

		# Reference to corresponding Repo object in the solver.
		self.solver_repo = None

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __cmp__(self, other):
		return cmp(self.priority * -1, other.priority * -1) or \
			cmp(self.name, other.name)

	@property
	def distro(self):
		"""
			Link to distro object.
		"""
		return self.pakfire.distro

	@property
	def priority(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Say if a repository is a local one or remotely located.

			Used to check if we need to download files.
		"""
		return False

	def update(self, force=False):
		"""
			A function that is called to update the local data of
			the repository.
		"""
		if hasattr(self, "index"):
			self.index.update(force)

	def get_all(self):
		"""
			Simply returns an instance of every package in this repository.
		"""
		for pkg in self.packages:
			yield pkg

	def get_by_name(self, name):
		for pkg in self.packages:
			if pkg.name == name:
				yield pkg

	def get_by_evr(self, name, evr):
		m = re.match(r"([0-9]+\:)?([0-9A-Za-z\.\-]+)-([0-9]+\.?[a-z0-9]+|[0-9]+)", evr)

		if not m:
			raise Exception, "Invalid input: %s" % evr

		(epoch, version, release) = m.groups()
		if epoch and epoch.endswith(":"):
			epoch = epoch[:-1]

		pkgs = [p for p in self.index.get_by_evr(name, epoch, version, release)]

		if not pkgs:
			return

		if not len(pkgs) == 1:
			raise Exception

		return pkgs[0]

	def get_by_glob(self, pattern):
		"""
			Returns a list of all packages that names match the glob pattern
			that is provided.
		"""
		for pkg in self.packages:
			if fnmatch.fnmatch(pkg.name, pattern):
				yield pkg

	def get_by_provides(self, requires):
		"""
			Returns a list of all packages that offer a matching "provides"
			of the given "requires".
		"""
		for pkg in self.packages:
			if pkg.does_provide(requires):
				yield pkg

	def get_by_requires(self, requires):
		"""
			Returns a list of all packages that require the given requirement.
		"""
		for pkg in self.packages:
			# XXX does not use the cmp() function of Requires.
			if requires.requires in pkg.requires:
				yield pkg

	def get_by_file(self, filename):
		for pkg in self.packages:
			match = False
			for pkg_filename in pkg.filelist:
				if fnmatch.fnmatch(pkg_filename, filename):
					match = True
					break

			if match:
				yield pkg

	def get_by_group(self, group):
		"""
			Get all packages that belong to a specific group.
		"""
		for pkg in self.packages:
			if group in pkg.groups:
				yield pkg

	def get_by_friendly_name(self, name):
		for pkg in self.packages:
			if pkg.friendly_name == name:
				return pkg

	def search(self, pattern):
		"""
			Returns a list of packages, that match the given pattern,
			which can be either a part of the name, summary or description
			or can be a glob pattern that matches one of these.
		"""
		for pkg in self.packages:
			for item in (pkg.name, pkg.summary, pkg.description):
				if pattern.lower() in item.lower() or \
						fnmatch.fnmatch(item, pattern):
					yield pkg

	@property
	def packages(self):
		"""
			Returns all packages.
		"""
		return self.index.packages

	@property
	def size(self):
		"""
			Return the number of packages.
		"""
		return self.index.size

	@property
	def filelist(self):
		if hasattr(self.index, "filelist"):
			return self.index.filelist

		return {}

	def import_to_solver(self, solver, repo):
		if hasattr(self, "index"):
			self.solver_repo = repo

			self.index.import_to_solver(solver, repo)
