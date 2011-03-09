#!/usr/bin/python


import fnmatch
import logging
import re

import util

import pakfire.depsolve
from pakfire.i18n import _

class Package(object):
	type = None # either "bin", "src" or "virt"

	def __init__(self, pakfire, repo=None):
		self.pakfire = pakfire
		self._repo = repo

		# Pointer to a package that is updated by this one.
		self.old_package = None

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.friendly_name)

	def __cmp__(self, other):
		# if packages differ names return in alphabetical order
		if not self.name == other.name:
			return cmp(self.name, other.name)

		# Compare the uuids: if packages have the same id they are totally equal.
		if self.uuid and other.uuid and self.uuid == other.uuid:
			return 0

		ret = util.version_compare(self.version_tuple, other.version_tuple)

		# XXX this is to move packages that have been built a while ago and
		# do not have all the meta information that they won't be evaluated
		# as the best match.
		if not ret:
			if "X"*3 in (self.build_id, other.build_id):
				if self.build_id == "X"*3 and not other.build_id == "X"*3:
					ret = -1

				elif not self.build_id == "X"*3 and other.build_id == "X"*3:
					ret = 1
		# XXX hack end

		# Compare the build times if we have a rebuilt package.
		if not ret and self.build_time and other.build_time:
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
			items.append((_("UUID"), self.uuid))
			items.append((_("Build ID"), self.build_id))
			items.append((_("Build date"), self.build_date))
			items.append((_("Build host"), self.build_host))

			caption = _("Provides")
			for prov in sorted(self.provides):
				items.append((caption, prov))
				caption = ""

			caption = _("Requires")
			for req in sorted(self.requires):
				items.append((caption, req))
				caption = ""

		format = "%%-%ds : %%s" % (max([len(k) for k, v in items]))

		s = []
		for caption, value in items:
			s.append(format % (caption, value))

		s.append("") # New line at the end

		# XXX why do we need to decode this?
		return "\n".join([str.decode("utf-8") for str in s])

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
		return "%s-%s.%s" % (self.name, self.friendly_version, self.arch)

	@property
	def friendly_version(self):
		s = "%s-%s" % (self.version, self.release)

		if self.epoch:
			s = "%d:%s" % (self.epoch, s)

		return s

	@property
	def repo(self):
		if self._repo:
			return self._repo

		# By default, every package is connected to a dummy repository
		return self.pakfire.repos.dummy

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
	def uuid(self):
		return self.metadata.get("PKG_UUID", None)

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

	def _does_provide_file(self, requires):
		for file in self.filelist:
			if fnmatch.fnmatch(file, requires.requires):
				return True

		return False

	def does_provide(self, requires):
		if not isinstance(requires, pakfire.depsolve.Requires):
			requires = pakfire.depsolve.Requires(self, requires)

		# Get all provide strings from the package data
		# and return true if requires is matched.
		if requires.requires in self.provides:
			return True

		if requires.type == "file":
			return self._does_provide_file(requires)

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

		elif requires.type == "virtual":
			(r_type, r_expr, r_name, r_version) = \
				util.parse_virtual_expr(requires.requires)

			# If we get an invalid expression with no name, we
			# do not provide this.
			if not r_name:
				return False

			for provides in self.provides:
				(p_type, p_expr, p_name, p_version) = \
					util.parse_virtual_expr(provides)

				# If name does not match, we have no match at all.
				if not p_type == r_type or not p_name == r_name:
					continue

				# Check if the expression is fulfilled.
				if r_expr == "=":
					return p_version == r_version

				elif r_expr == ">=":
					return p_version >= r_version

				elif r_expr == ">":
					return p_version > r_version

				elif r_expr == "<":
					return p_version < r_version

				elif r_expr == "<=":
					return p_version <= r_version

				elif not r_expr:
					# If we get here, the name matches and there was no version
					# required.
					return True

		# No match was found at all
		return False

	def extract(self, path):
		raise NotImplementedError

