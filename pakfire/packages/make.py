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

import logging
import os
import re
import shutil
import socket
import tarfile

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.progress import TextMeter

import lexer
import packager

import pakfire.chroot as chroot
import pakfire.util as util

from base import Package
from file import SourcePackage

from pakfire.constants import *
from pakfire.i18n import _

# XXX to be moved to pakfire.downloader
class SourceDownloader(object):
	def __init__(self, pakfire, mirrors=None):
		self.pakfire = pakfire
		self.mirrors = mirrors

		# XXX need to use downloader.py
		self.grabber = URLGrabber(
			prefix = self.pakfire.config.get("source_download_url"),
			progress_obj = TextMeter(),
			quote = 0,
		)

	def download(self, filename):
		filename = os.path.join(SOURCE_CACHE_DIR, filename)

		if os.path.exists(filename):
			return filename

		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		try:
			self.grabber.urlgrab(os.path.basename(filename), filename=filename)
		except URLGrabError, e:
			raise DownloadError, "%s %s" % (os.path.basename(filename), e)

		return filename


class MakefileBase(Package):
	def __init__(self, pakfire, filename):
		Package.__init__(self, pakfire)

		# Save the filename of the makefile.
		self.filename = os.path.abspath(filename)

		# Open and parse the makefile.
		# XXX pass environment to lexer
		self.lexer = lexer.RootLexer.open(self.filename,
			environ=self.pakfire.environ)

	@property
	def package_filename(self):
		return PACKAGE_FILENAME_FMT % {
			"arch"    : self.arch,
			"ext"     : PACKAGE_EXTENSION,
			"name"    : self.name,
			"release" : self.release,
			"version" : self.version,
		}

	def lint(self):
		errors = []

		if not self.name:
			errors.append(_("Package name is undefined."))

		if not self.version:
			errors.append(_("Package version is undefined."))

		# XXX to do...

		return errors

	@property
	def name(self):
		return self.lexer.get_var("name")

	@property
	def epoch(self):
		epoch = self.lexer.get_var("epoch")
		if not epoch:
			return 0

		return int(epoch)

	@property
	def version(self):
		return self.lexer.get_var("version")

	@property
	def release(self):
		release = self.lexer.get_var("release")
		assert release

		tag = self.lexer.get_var("DISTRO_DISTTAG")
		assert tag

		return ".".join((release, tag))

	@property
	def summary(self):
		return self.lexer.get_var("summary")

	@property
	def description(self):
		description = self.lexer.get_var("description")

		# Replace all backslashes at the end of a line.
		return description.replace("\\\n", "\n")

	@property
	def groups(self):
		groups = self.lexer.get_var("groups").split()

		return sorted(groups)

	@property
	def url(self):
		return self.lexer.get_var("url")

	@property
	def license(self):
		return self.lexer.get_var("license")

	@property
	def maintainer(self):
		maintainer = self.lexer.get_var("maintainer")

		if not maintainer:
			maintainer = self.lexer.get_var("DISTRO_MAINTAINER")

		return maintainer

	@property
	def vendor(self):
		return self.lexer.get_var("DISTRO_VENDOR")

	@property
	def build_host(self):
		return socket.gethostname()

	# XXX build_id and build_time are used to create a source package

	@property
	def build_id(self):
		# XXX todo
		# Not existant for Makefiles
		return None

	@property
	def build_time(self):
		# XXX todo
		# Not existant for Makefiles
		return None


class Makefile(MakefileBase):
	@property
	def uuid(self):
		hash1 = util.calc_hash1(self.filename)

		# Return UUID version 5 (SHA1 hash)
		return "%8s-%4s-5%3s-%4s-%11s" % \
			(hash1[0:8], hash1[9:13], hash1[14:17], hash1[18:22], hash1[23:34])

	@property
	def path(self):
		return os.path.dirname(self.filename)

	@property
	def arch(self):
		"""
			This is only used to create the name of the source package.
		"""
		return "src"

	@property
	def packages(self):
		pkgs = []

		for lexer in self.lexer.packages:
			name = lexer.get_var("_name")

			pkg = MakefilePackage(self.pakfire, name, lexer)
			pkgs.append(pkg)

		return pkgs

	@property
	def source_dl(self):
		dls = []

		if self.pakfire.distro.source_dl:
			dls.append(self.pakfire.distro.source_dl)

		dl = self.lexer.get_var("source_dl")
		if dl:
			dls.append(dl)

		return dls

	def download(self):
		"""
			Download all external sources and return a list with the local
			copies.
		"""
		# Download source files.
		# XXX need to implement mirrors
		downloader = SourceDownloader(self.pakfire, mirrors=self.source_dl)

		files = []
		for filename in self.sources:
			filename = downloader.download(filename)
			files.append(filename)

		return files

	def dist(self, resultdirs):
		"""
			Create a source package.

			We assume that all required files are in /build.
		"""
		#dump = self.dump()
		#for line in dump.splitlines():
		#	logging.info(line)

		p = packager.SourcePackager(self.pakfire, self)
		p.run(resultdirs)

	def dump(self, *args, **kwargs):
		dump = MakefileBase.dump(self, *args, **kwargs)
		dump = dump.splitlines()

		#dump += ["", _("Containing the following binary packages:"),]
		#
		#for pkg in self.packages:
		#	_dump = pkg.dump(*args, **kwargs)
		#
		#	for line in _dump.splitlines():
		#		dump.append("  %s" % line)
		#	dump.append("")

		return "\n".join(dump)

	def get_buildscript(self, stage):
		return self.lexer.build.get_var("_%s" % stage)

	@property
	def prerequires(self):
		return []

	@property
	def requires(self):
		return self.lexer.build.get_var("requires", "").split()

	@property
	def provides(self):
		return []

	@property
	def obsoletes(self):
		return []

	@property
	def conflicts(self):
		return []

	@property
	def files(self):
		files = []
		basedir = os.path.dirname(self.filename)

		for dirs, subdirs, _files in os.walk(basedir):
			for f in _files:
				files.append(os.path.join(dirs, f))

		return files

	@property
	def sources(self):
		return self.lexer.get_var("sources").split()

	@property
	def exports(self):
		exports = {}

		# Include quality agent exports.
		exports.update(self.lexer.quality_agent.exports)

		for export in self.lexer.build.exports:
			exports[export] = self.lexer.build.get_var(export)

		return exports

	def extract(self, message=None, prefix=None):
		# XXX neeed to make this waaaaaaaaaay better.

		files = self.files

		# Load progressbar.
		pb = None
		if message:
			message = "%-10s : %s" % (message, self.friendly_name)
			pb = util.make_progress(message, len(files), eta=False)

		dir_len = len(os.path.dirname(self.filename))

		# Copy all files that belong to the package
		i = 0
		for f in files:
			if pb:
				i += 1
				pb.update(i)

			_f = f[dir_len:]
			logging.debug("%s/%s" % (prefix, _f))
	
			path = "%s/%s" % (prefix, _f)

			path_dir = os.path.dirname(path)
			if not os.path.exists(path_dir):
				os.makedirs(path_dir)

			shutil.copy2(f, path)

		if pb:
			pb.finish()

		# Download source files.
		downloader = SourceDownloader(self.pakfire, mirrors=self.source_dl)
		for filename in self.sources:
			_filename = downloader.download(filename)
			assert _filename

			filename = "%s/files/%s" % (prefix, os.path.basename(_filename))
			dirname = os.path.dirname(filename)

			if not os.path.exists(dirname):
				os.makedirs(dirname)
				
			shutil.copy2(_filename, filename)

	@property
	def inst_size(self):
		return 0


class MakefilePackage(MakefileBase):
	def __init__(self, pakfire, name, lexer):
		Package.__init__(self, pakfire)

		self._name = name
		self.lexer = lexer

		# Store additional dependencies in here.
		self._dependencies = {}

	@property
	def name(self):
		return self._name

	@property
	def arch(self):
		return self.lexer.get_var("arch", "%{DISTRO_ARCH}")

	@property
	def configfiles(self):
		return self.lexer.get_var("configfiles").split()

	@property
	def files(self):
		return self.lexer.get_var("files").split()

	@property
	def uuid(self):
		return None

	def track_dependencies(self, builder, path):
		result = builder.do("/usr/lib/buildsystem-tools/dependency-tracker %s" \
			% path, returnOutput=True)

		for line in result.splitlines():
			m = re.match(r"^(\w+)=(.*)$", line)
			if m is None:
				continue

			key, val = m.groups()

			if not key in ("prerequires", "requires", "provides", "conflicts", "obsoletes",):
				continue

			val = val.strip("\"")
			val = val.split()

			self._dependencies[key] = sorted(val)

	def get_deps(self, key):
		# Collect all dependencies that were set in the makefile by the user.
		deps = self.lexer.get_var(key).split()

		# Collect all dependencies that were discovered by the tracker.
		deps += self._dependencies.get(key, [])

		# Remove duplicates.
		deps = set(deps)
		deps = list(deps)

		return sorted(deps)

	@property
	def prerequires(self):
		return self.get_deps("prerequires")

	@property
	def requires(self):
		return self.get_deps("requires")

	@property
	def provides(self):
		return self.get_deps("provides")

	@property
	def obsoletes(self):
		return self.get_deps("obsoletes")

	@property
	def conflicts(self):
		return self.get_deps("conflicts")

	def get_scriptlet(self, type):
		return self.lexer.scriptlets.get(type, None)

	@property
	def inst_size(self):
		# The size of this is unknown.
		return 0
