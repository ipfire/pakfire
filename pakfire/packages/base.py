#!/usr/bin/python

import logging
import re

import util

import pakfire.depsolve
from pakfire.i18n import _

class Package(object):
	type = None # either "bin", "src" or "virt"

	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self._repo = repo

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.friendly_name)

	def __cmp__(self, other):
		# if packages differ names return in alphabetical order
		if not self.name == other.name:
			return cmp(self.name, other.name)

		ret = util.version_compare(self.version_tuple, other.version_tuple)

		# Compare the build times if we have a rebuilt package.
		if not ret:
			ret = cmp(self.build_time, other.build_time)

		#if ret == 0:
		#	logging.debug("%s is equal to %s" % (self, other))
		#elif ret < 0:
		#	logging.debug("%s is more recent than %s" % (other, self))
		#elif ret > 0:
		#	logging.debug("%s is more recent than %s" % (self, other))

		# If no rank could be created, sort by repository priority
		if not ret:
			ret = cmp(self.repo, other.repo)

		return ret

	def dump(self, short=False, long=False):
		if short:
			return "%s.%s : %s" % (self.name, self.arch, self.summary)

		items = [
			(_("Name"), self.name),
			(_("Arch"), self.arch),
			(_("Version"), self.version),
			(_("Release"), self.release),
			(_("Size"), util.format_size(self.size)),
			(_("Repo"), self.repo.name),
			(_("Summary"), self.summary),
			(_("URL"), self.url),
			(_("License"), self.license),
		]

		caption = _("Description")
		for line in util.text_wrap(self.description):
			items.append((caption, line))
			caption = ""

		if long:
			items.append((_("Build ID"), self.build_id))
			items.append((_("Build date"), self.build_date))
			items.append((_("Build host"), self.build_host))

		format = "%%-%ds : %%s" % (max([len(k) for k, v in items]))

		s = []
		for caption, value in items:
			s.append(format % (caption, value))

		s.append("") # New line at the end

		return "\n".join(s)

	@property
	def info(self):
		info = {
			"name"        : self.name,
			"version"     : self.version,
			"release"     : self.release,
			"epoch"       : self.epoch,
			"arch"        : self.arch,
			"group"       : self.group,
			"summary"     : self.summary,
			"description" : self.description,
			"maintainer"  : self.maintainer,
			"url"         : self.url,
			"license"     : self.license,
		}

		return info

	@property
	def size(self):
		"""
			Return the size of the package file.

			This should be overloaded by another class and returns 0 for
			virtual packages.
		"""
		return 0

	@property
	def local(self):
		"""
			Indicates whether a package is located "local" means on disk
			and has not be downloaded.
		"""
		return False

	### META INFORMATION ###

	@property
	def metadata(self):
		raise NotImplementedError

	@property
	def friendly_name(self):
		return "%s-%s" % (self.name, self.friendly_version)

	@property
	def friendly_version(self):
		s = "%s-%s" % (self.version, self.release)

		if self.epoch:
			s = "%d:%s" % (self.epoch, s)

		return s

	@property
	def repo(self):
		return self._repo

	@property
	def name(self):
		return self.metadata.get("PKG_NAME")

	@property
	def version(self):
		return self.metadata.get("PKG_VER")

	@property
	def release(self):
		ret = None

		for i in ("PKG_RELEASE", "PKG_REL"):
			ret = self.metadata.get(i, None)
			if ret:
				break

		return ret

	@property
	def epoch(self):
		epoch = self.metadata.get("PKG_EPOCH", 0)

		return int(epoch)

	@property
	def version_tuple(self):
		"""
			Returns a tuple like (epoch, version, release) that can
			be used to compare versions of packages.
		"""
		return (self.epoch, self.version, self.release)

	@property
	def arch(self):
		raise NotImplementedError

	@property
	def maintainer(self):
		return self.metadata.get("PKG_MAINTAINER")

	@property
	def license(self):
		return self.metadata.get("PKG_LICENSE")

	@property
	def summary(self):
		return self.metadata.get("PKG_SUMMARY")

	@property
	def description(self):
		return self.metadata.get("PKG_DESCRIPTION")

	@property
	def group(self):
		return self.metadata.get("PKG_GROUP")

	@property
	def url(self):
		return self.metadata.get("PKG_URL")

	@property
	def triggers(self):
		triggers = self.metadata.get("PKG_TRIGGERS", "")

		return triggers.split()

	@property
	def signature(self):
		raise NotImplementedError

	@property
	def build_date(self):
		return self.metadata.get("BUILD_DATE")

	@property
	def build_host(self):
		return self.metadata.get("BUILD_HOST")

	@property
	def build_id(self):
		return self.metadata.get("BUILD_ID")

	@property
	def build_time(self):
		build_time = self.metadata.get("BUILD_TIME", 0)

		return int(build_time)

	@property
	def _provides(self):
		# Make package identifyable by its name and version/release tuples.
		provides = [
			self.name,
			"%s=%s-%s" % (self.name, self.version, self.release),
			"%s=%s:%s-%s" % (self.name, self.epoch, self.version, self.release),
		]

		return provides

	### methods ###

	def does_provide(self, requires):
		if not isinstance(requires, pakfire.depsolve.Requires):
			requires = pakfire.depsolve.Requires(self, requires)

		# If the provides string equals the name of the package, we
		# return true.
		if self.name == requires.requires:
			return True

		# Get all provide strings from the package data
		# and return true if requires is matched.
		if requires.requires in self.provides:
			return True

		if requires.type == "file":
			return requires.requires in self.filelist

		elif requires.type == "expr":
			# Handle all expressions like "gcc>=4.0.0-1"
			(e_expr, e_name, e_epoch, e_version, e_release) = \
				util.parse_pkg_expr(requires.requires)

			# If the package names do not match, we do not provide this:
			if not self.name == e_name:
				return False

			ret = util.version_compare(self.version_tuple, (e_epoch, e_version, e_release))

			# If we equal the version, we provide this
			if "=" in e_expr and ret == 0:
				return True

			elif ">" in e_expr and ret > 0:
				return True

			elif "<" in e_expr and ret < 0:
				return True

			return False

		# No match was found at all
		return False

	def extract(self, path):
		raise NotImplementedError

