#!/usr/bin/python

import logging
import re

import packages
import repository

from errors import *

class Requires(object):
	def __init__(self, pkg, requires):
		self.pkg = pkg
		self.requires = requires

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.requires)

	def __str__(self):
		return self.requires

	def __cmp__(self, other):
		return cmp(self.requires, other.requires)

	@property
	def type(self):
		if self.requires.startswith("/"):
			return "file"

		elif ">" in self.requires or "<" in self.requires or "=" in self.requires:
			return "expr"

		elif not re.match("^lib.*\.so.*", self.requires):
			return "lib"

		return "generic"


class Conflicts(object):
	def __init__(self, pkg, conflicts):
		self.pkg = pkg
		self.conflicts = conflicts

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.conflicts)

	def __str__(self):
		return self.conflicts


class Obsoletes(object):
	def __init__(self, pkg, obsoletes):
		self.pkg = pkg
		self.obsoletes = obsoletes

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.obsoletes)

	def __str__(self):
		return self.obsoletes


class DependencySet(object):
	def __init__(self, pakfire):
		# Reference all repositories
		self.repos = pakfire.repos #repository.Repositories()

		# List of packages in this set
		self.__packages = []

		# Helper lists
		self.__conflicts = []
		self.__requires = []
		self.__obsoletes = []

		# Read-in all packages from the database that have
		# been installed previously and need to be taken into
		# account when resolving dependencies.
		for pkg in self.repos.local.packages:
			self.add_package(pkg)

	def add_requires(self, requires, pkg=None):
		# XXX for now, we skip the virtual perl requires
		if requires.startswith("perl(") or requires.startswith("perl>") or requires.startswith("perl="):
			return

		requires = Requires(pkg, requires)

		if requires in self.__requires:
			return

		for pkg in self.__packages:
			if pkg.does_provide(requires):
				logging.debug("Skipping requires '%s' which is already provided by %s" % (requires.requires, pkg))
				return

		#logging.debug("Adding requires: %s" % requires)
		self.__requires.append(requires)

	def add_obsoletes(self, obsoletes, pkg=None):
		obsoletes = Obsoletes(pkg, obsoletes)

		self.__obsoletes.append(obsoletes)

	def add_package(self, pkg):
		#print pkg, sorted(self.__packages)
		#assert not pkg in self.__packages
		if pkg in self.__packages:
			logging.debug("Trying to add package which is already in the dependency set: %s" % pkg)
			return

		if not isinstance(pkg, packages.DatabasePackage):
			logging.info(" --> Adding package to dependency set: %s" % pkg.friendly_name)
		self.__packages.append(pkg)

		# Add the requirements of the newly added package.
		for req in pkg.requires:
			self.add_requires(req, pkg)

		# Remove all requires that are fulfilled by this package.
		# For that we copy the matching requires to _requires and remove them
		# afterwards, because changing self.__requires in a "for" loop is not
		# a good idea.
		_requires = []
		for req in self.__requires:
			if pkg.does_provide(req):
				_requires.append(req)

		for req in _requires:
			self.__requires.remove(req)

	@property
	def packages(self):
		if not self.__requires:
			return self.__packages[:]

	def resolve(self):
		unresolveable_reqs = []

		while self.__requires:
			requires = self.__requires.pop(0)
			logging.debug("Resolving requirement \"%s\"" % requires)

			# Fetch all candidates from the repositories and save the
			# best one
			candidates = packages.PackageListing(self.repos.get_by_provides(requires))

			if not candidates:
				logging.debug("  Got no candidates for that")
				unresolveable_reqs.append(requires)
				continue

			logging.debug("  Got candidates for that:")
			for candidate in candidates:
				logging.debug("  --> %s" % candidate)

			best = candidates.get_most_recent()
			if best:
				self.add_package(best)

		if unresolveable_reqs:
			raise DependencyError, "Cannot resolve %s" % \
				" ".join([r.requires for r in unresolveable_reqs])

