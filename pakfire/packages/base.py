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

		ret = util.version_compare((self.epoch, self.version, self.release),
			(other.epoch, other.version, other.release))

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

	def dump(self, short=False):
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

	### methods ###

	def does_provide(self, requires):
		if not isinstance(requires, pakfire.depsolve.Requires):
			requires = pakfire.depsolve.Requires(self, requires)

		# If the provides string equals the name of the package, we
		# return true.
		if self.name == requires.requires:
			return True

		if requires.type == "file":
			return requires.requires in self.filelist

		# Get all provide strings from the package data
		# and return true if requires is matched. Otherwise return false.
		provides = self.provides

		return requires.requires in provides
		
		# XXX this function has to do lots more of magic:
		#  e.g. filename matches, etc.

	def extract(self, path):
		raise NotImplementedError

