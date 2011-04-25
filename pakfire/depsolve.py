#!/usr/bin/python

import logging
import re

import packages
import repository
import transaction
import util

from errors import *

from i18n import _

PKG_DUMP_FORMAT = " %-21s %-8s %-21s %-19s %5s "

class Requires(object):
	def __init__(self, pkg, requires, dep=False):
		self.pkg = pkg
		self.requires = requires
		self.dep = dep

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.requires)

	def __str__(self):
		return self.requires

	def __cmp__(self, other):
		return cmp(self.requires, other.requires)

	def __hash__(self):
		return hash(self.requires)

	@property
	def type(self):
		if self.requires.startswith("/"):
			return "file"

		elif "(" in self.requires:
			return "virtual"

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

	def __hash__(self):
		return hash(self.conflicts)


class Obsoletes(object):
	def __init__(self, pkg, obsoletes):
		self.pkg = pkg
		self.obsoletes = obsoletes

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.obsoletes)

	def __str__(self):
		return self.obsoletes

	def __hash__(self):
		return hash(self.obsoletes)


class DependencySet(object):
	def __init__(self, pakfire):
		# Reference all repositories
		self.repos = pakfire.repos #repository.Repositories()

		# List of packages in this set
		self.__packages = set()

		# Helper lists
		self.__conflicts = set()
		self.__requires = set()
		self.__obsoletes = set()

		# Create a new transaction set.
		self.ts = transaction.TransactionSet()

		# Read-in all packages from the database that have
		# been installed previously and need to be taken into
		# account when resolving dependencies.
		for pkg in self.repos.local.packages:
			self.add_package(pkg, transaction=False)

	def add_requires(self, requires, pkg=None, dep=False):
		requires = Requires(pkg, requires, dep)

		if requires in self.__requires:
			return

		for pkg in self.__packages:
			if pkg.does_provide(requires):
				logging.debug("Skipping requires '%s' which is already provided by %s" % (requires.requires, pkg))
				return

		#logging.debug("Adding requires: %s" % requires)
		self.__requires.add(requires)

	def add_obsoletes(self, obsoletes, pkg=None):
		obsoletes = Obsoletes(pkg, obsoletes)

		self.__obsoletes.add(obsoletes)

	def add_package(self, pkg, dep=False, transaction=True):
		#print pkg, sorted(self.__packages)
		#assert not pkg in self.__packages
		if pkg in self.__packages:
			logging.debug("Trying to add package which is already in the dependency set: %s" % pkg)
			return

		if transaction:
			transaction_mode = "install"
			for p in self.__packages:
				if pkg.name == p.name:
					transaction_mode = "update"

					# Set pointer to package that is updated.
					pkg.old_package = p

					break

			# Add package to transaction set
			func = getattr(self.ts, transaction_mode)
			func(pkg, dep=dep)

		#if not isinstance(pkg, packages.DatabasePackage):
		#	logging.info(" --> Adding package to dependency set: %s" % pkg.friendly_name)
		self.__packages.add(pkg)

		# Add the requirements of the newly added package.
		for req in pkg.requires:
			self.add_requires(req, pkg, dep=True)

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
			requires = self.__requires.pop()
			logging.debug("Resolving requirement \"%s\"" % requires)

			# Fetch all candidates from the repositories and save the
			# best one
			if requires.type == "file":
				candidates = self.repos.get_by_file(requires.requires)
			else:
				candidates = self.repos.get_by_provides(requires)

			# Turn the candidates into a package listing.
			candidates = packages.PackageListing(candidates)

			if not candidates:
				logging.debug("  Got no candidates for that")
				unresolveable_reqs.append(requires)
				continue

			logging.debug("  Got candidates for that:")
			for candidate in candidates:
				logging.debug("  --> %s" % candidate)

			best = candidates.get_most_recent()
			if best:
				self.add_package(best, dep=requires.dep)

		if unresolveable_reqs:
			raise DependencyError, "Cannot resolve %s" % \
				" ".join([r.requires for r in unresolveable_reqs])

	def dump_pkg(self, format, pkg):
		return format % (
			pkg.name,
			pkg.arch,
			pkg.friendly_version,
			pkg.repo.name,
			util.format_size(pkg.size),
		)

	def dump_pkgs(self, caption, pkgs):
		if not pkgs:
			return []

		s = [caption,]
		for pkg in sorted(pkgs):
			s.append(self.dump_pkg(PKG_DUMP_FORMAT, pkg))
		s.append("")
		return s

	def dump(self, logger=None):
		# If no logger was given, we use the root logger.
		if not logger:
			logger = logging.getLogger()

		width = 80
		line = "=" * width

		s = []
		s.append(line)
		s.append(PKG_DUMP_FORMAT % (_("Package"), _("Arch"), _("Version"), _("Repository"), _("Size")))
		s.append(line)

		s += self.dump_pkgs(_("Installing:"), self.ts.installs)
		s += self.dump_pkgs(_("Installing for dependencies:"), self.ts.install_deps)
		s += self.dump_pkgs(_("Updating:"), self.ts.updates)
		s += self.dump_pkgs(_("Updating for dependencies:"), self.ts.update_deps)
		s += self.dump_pkgs(_("Removing:"), self.ts.removes)
		s += self.dump_pkgs(_("Removing for dependencies:"), self.ts.remove_deps)

		s.append(_("Transaction Summary"))
		s.append(line)

		format = "%-20s %-4d %s"

		if self.ts.installs or self.ts.install_deps:
			s.append(format % (_("Install"),
				len(self.ts.installs + self.ts.install_deps), _("Package(s)")))

		if self.ts.updates or self.ts.update_deps:
			s.append(format % (_("Updates"),
				len(self.ts.updates + self.ts.update_deps), _("Package(s)")))

		if self.ts.removes or self.ts.remove_deps:
			s.append(format % (_("Remove"),
				len(self.ts.removes + self.ts.remove_deps), _("Package(s)")))

		# Calculate the size of all files that need to be downloaded this this
		# transaction.
		download_size = sum([p.size for p in self.ts.downloads])
		if download_size:
			s.append(_("Total download size: %s") % util.format_size(download_size))
		s.append("")

		for line in s:
			logger.info(line)
