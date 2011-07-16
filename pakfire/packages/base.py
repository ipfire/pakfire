#!/usr/bin/python

import datetime
import logging
import xml.sax.saxutils

import util

from pakfire.i18n import _

class Package(object):
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

	def __hash__(self):
		hashstr = ["%s" % s for s in (self.name, self.epoch, self.version,
			self.release, self.arch,)]

		return hash("-".join(hashstr))

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
			(_("Groups"), " ".join(self.groups)),
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
			"groups"      : self.groups,
			"summary"     : self.summary,
			"description" : self.description,
			"maintainer"  : self.maintainer,
			"url"         : self.url,
			"license"     : self.license,
			"hash1"       : self.hash1,
			"vendor"      : self.vendor,
			"build_host"  : self.build_host,
			"build_time"  : self.build_time,
			"size"        : self.size,
			"inst_size"   : self.inst_size,
		}

		return info

	@property
	def hash1(self):
		return "0"*40

	@property
	def size(self):
		"""
			Return the size of the package file.

			This should be overloaded by another class and returns 0 for
			virtual packages.
		"""
		return 0

	@property
	def inst_size(self):
		# XXX to be done
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
	def base(self):
		"""
			Say if a package belongs to the basic set
			that is installed by default.
		"""
		return "Base" in self.groups

	@property
	def critical(self):
		"""
			Return if a package is marked "critial".
		"""
		return "Critical" in self.groups

	@property
	def type(self):
		return self.metadata.get("TYPE", "unknown")

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
	def groups(self):
		return self.metadata.get("PKG_GROUPS", "").split()

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
		"""
			Automatically convert the UNIX timestamp from self.build_time to
			a humanly readable format.
		"""
		return "%s UTC" % datetime.datetime.utcfromtimestamp(self.build_time)

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
	def supported_arches(self):
		return self.metadata.get("PKG_SUPPORTED_ARCHES", "all")

	@property
	def vendor(self):
		return self.metadata.get("PKG_VENDOR", "")

	@property
	def pre_requires(self):
		return set() # XXX to be done

	@property
	def requires(self):
		ret = ""

		# The default attributes, that are process for the requires.
		attrs = ("PKG_REQUIRES", "PKG_DEPS")

		# Source packages do depend on their build dependencies.
		if self.arch == "src":
			attrs = ("PKG_BUILD_DEPS",)

		for i in attrs:
			ret = self.metadata.get(i, ret)
			if ret:
				break

		return set(ret.split())

	@property
	def provides(self):
		provides = self.metadata.get("PKG_PROVIDES", "").split()

		return set(provides)

	@property
	def conflicts(self):
		conflicts = self.metadata.get("PKG_CONFLICTS", "").split()

		return set(conflicts)

	@property
	def obsoletes(self):
		obsoletes = self.metadata.get("PKG_OBSOLETES", "").split()

		return set(obsoletes)

	def extract(self, path, prefix=None):
		raise NotImplementedError, "%s" % repr(self)
