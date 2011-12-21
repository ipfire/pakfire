#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import datetime
import os
import shutil
import xml.sax.saxutils

import logging
log = logging.getLogger("pakfire")

import pakfire.util as util

from pakfire.constants import *
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

		# If UUIDs match, the packages are absolutely equal.
		if self.uuid == other.uuid:
			#log.debug("%s is equal to %s by UUID" % (self, other))
			return 0

		ret = util.version_compare(self.pakfire.pool,
			self.friendly_version, other.friendly_version)

		# XXX this is to move packages that have been built a while ago and
		# do not have all the meta information that they won't be evaluated
		# as the best match.
		#if not ret:
		#	if "X"*3 in (self.build_id, other.build_id):
		#		if self.build_id == "X"*3 and not other.build_id == "X"*3:
		#			ret = -1
		#
		#		elif not self.build_id == "X"*3 and other.build_id == "X"*3:
		#			ret = 1
		# XXX hack end

		# Compare the build times if we have a rebuilt package.
		if not ret and self.build_time and other.build_time:
			ret = cmp(self.build_time, other.build_time)

		#if ret == 0:
		#	log.debug("%s is equal to %s" % (self, other))
		#elif ret < 0:
		#	log.debug("%s is more recent than %s" % (other, self))
		#elif ret > 0:
		#	log.debug("%s is more recent than %s" % (self, other))

		# If no rank could be created, sort by repository priority
		if not ret:
			ret = cmp(self.repo, other.repo)

		return ret

	def __hash__(self):
		hashstr = ["%s" % s for s in (self.name, self.epoch, self.version,
			self.release, self.arch,)]

		return hash("-".join(hashstr))

	def dump(self, short=False, long=False, filelist=False):
		if short:
			return "%s.%s : %s" % (self.name, self.arch, self.summary)

		items = [
			(_("Name"), self.name),
		]

		# Show supported arches if available.
		if hasattr(self, "supported_arches") and not self.supported_arches == "all":
			arch = "%s (%s)" % (self.arch, self.supported_arches)
		else:
			arch = self.arch
		items.append((_("Arch"), arch))

		items += [
			(_("Version"), self.version),
			(_("Release"), self.release),
		]

		if self.size:
			items.append((_("Size"), util.format_size(self.size)))

		# filter dummy repository
		if not self.repo == self.pakfire.repos.dummy:
			items.append((_("Repo"), self.repo.name))

		items += [
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
			if self.maintainer:
				items.append((_("Maintainer"), self.maintainer))

			items.append((_("Vendor"), self.vendor))

			items.append((_("UUID"), self.uuid))
			items.append((_("Build ID"), self.build_id))
			items.append((_("Build date"), self.build_date))
			items.append((_("Build host"), self.build_host))

			caption = _("Provides")
			for prov in sorted(self.provides):
				items.append((caption, prov))
				caption = ""

			caption = _("Pre-requires")
			for req in sorted(self.prerequires):
				items.append((caption, req))
				caption = ""

			caption = _("Requires")
			for req in sorted(self.requires):
				items.append((caption, req))
				caption = ""

			caption = _("Conflicts")
			for req in sorted(self.conflicts):
				items.append((caption, req))
				caption = ""

			caption = _("Obsoletes")
			for req in sorted(self.obsoletes):
				items.append((caption, req))
				caption = ""

		# Append filelist if requested.
		if filelist:
			for file in self.filelist:
				items.append((_("File"), file))

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
			"build_date"  : self.build_date,
			"build_host"  : self.build_host,
			"build_id"    : self.build_id,
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
		"""
			The used disk space when the package is installed.

			Returns None if inst_size is unknown.
		"""
		return None

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
		raise NotImplementedError, self

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

	def is_installed(self):
		return self.repo.name == "@system"

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
		if self.build_time is None:
			return _("Not set")

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
	def prerequires(self):
		requires = self.metadata.get("PKG_PREREQUIRES", "")

		return requires.split()

	@property
	def requires(self):
		ret = ""

		# The default attributes, that are process for the requires.
		attrs = ["PKG_REQUIRES", "PKG_DEPS",]

		if self.arch == "src":
			attrs += ["PKG_BUILD_DEPS",]

		for i in attrs:
			ret = self.metadata.get(i, ret)
			if ret:
				break

		return ret.splitlines()

	@property
	def provides(self):
		return self.metadata.get("PKG_PROVIDES", "").splitlines()

	@property
	def conflicts(self):
		return self.metadata.get("PKG_CONFLICTS", "").splitlines()

	@property
	def obsoletes(self):
		return self.metadata.get("PKG_OBSOLETES", "").splitlines()

	@property
	def scriptlets(self):
		return self.metadata.get("PKG_SCRIPTLETS", "").splitlines()

	@property
	def filelist(self):
		raise NotImplementedError

	def extract(self, path, prefix=None):
		raise NotImplementedError, "%s" % repr(self)

	def remove(self, message=None, prefix=None):
		# Make two filelists. One contains all binary files that need to be
		# removed, the other one contains the configuration files which are
		# kept. files and configfiles are disjunct.
		files = []
		configfiles = self.configfiles

		for file in self.filelist:
			if file in configfiles:
				continue

			assert file.startswith("/")
			files.append(file)

		self._remove_files(files, message, prefix)

	def _remove_files(self, files, message, prefix):
		if prefix in ("/", None):
			prefix = ""

		# Load progressbar.
		pb = None
		if message:
			message = "%-10s : %s" % (message, self.friendly_name)
			pb = util.make_progress(message, len(files), eta=False)

		# Sort files by the length of their name to remove all files in
		# a directory first and then check, if there are any files left.
		files.sort(cmp=lambda x,y: cmp(len(x.name), len(y.name)), reverse=True)

		# Messages to the user.
		messages = []

		i = 0
		for _file in files:
			# Update progress.
			if pb:
				i += 1
				pb.update(i)

			log.debug("Removing file: %s" % _file)

			if prefix:
				file = os.path.join(prefix, _file.name[1:])
				assert file.startswith("%s/" % prefix)
			else:
				file = _file.name

			# If the file was removed by the user, we can skip it.
			if not os.path.exists(file):
				continue

			# Rename configuration files.
			if _file.is_config():
				file_save = "%s%s" % (file, CONFIG_FILE_SUFFIX_SAVE)

				try:
					shutil.move(file, file_save)
				except shutil.Error, e:
					print e

				if prefix:
					file_save = os.path.relpath(file_save, prefix)
				messages.append(_("Config file saved as %s.") % file_save)
				continue

			# Handle regular files and symlinks.
			if os.path.isfile(file) or os.path.islink(file):
				try:
					os.remove(file)
				except OSError:
					log.error("Cannot remove file: %s. Remove manually." % _file)

			# Handle directories.
			# Skip removal if the directory is a mountpoint.
			elif os.path.isdir(file) and not os.path.ismount(file):
				# Try to remove the directory. If it is not empty, OSError is raised,
				# but we are okay with that.
				try:
					os.rmdir(file)
				except OSError:
					pass

			# Log all unhandled types.
			else:
				log.warning("Cannot remove file: %s. Filetype is unhandled." % file)

		if pb:
			pb.finish()

		for msg in messages:
			log.warning(msg)
