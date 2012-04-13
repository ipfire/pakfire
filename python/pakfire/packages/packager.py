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

import collections
import fnmatch
import glob
import hashlib
import os
import progressbar
import re
import shutil
import sys
import tarfile
import tempfile
import time
import uuid
import zlib

import logging
log = logging.getLogger("pakfire")

import pakfire.lzma as lzma
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

from file import BinaryPackage, InnerTarFile, InnerTarFileXz, SourcePackage

class Packager(object):
	payload_compression = None

	def __init__(self, pakfire, pkg):
		self.pakfire = pakfire
		self.pkg = pkg

		self.files = []
		self.tmpfiles = []

	def __del__(self):
		for file in self.tmpfiles:
			if not os.path.exists(file):
				continue

			log.debug("Removing tmpfile: %s" % file)

			if os.path.isdir(file):
				util.rm(file)
			else:
				os.remove(file)

	def mktemp(self, directory=False):
		if directory:
			filename = os.path.join("/", LOCAL_TMP_PATH, util.random_string())
			os.makedirs(filename)
		else:
			f = tempfile.NamedTemporaryFile(mode="w", delete=False)
			f.close()

			filename = f.name

		self.tmpfiles.append(filename)

		return filename

	def save(self, filename):
		# Create a new tar archive.
		tar = tarfile.TarFile(filename, mode="w", format=tarfile.PAX_FORMAT)

		# Add package formation information.
		# Must always be the first file in the archive.
		formatfile = self.create_package_format()
		tar.add(formatfile, arcname="pakfire-format")

		# XXX make sure all files belong to the root user

		# Create checksum file.
		chksumsfile = self.mktemp()
		chksums = open(chksumsfile, "w")

		# Add all files to tar file.
		for arcname, filename in self.files:
			tar.add(filename, arcname=arcname)

			# Calculating the hash sum of the added file
			# and store it in the chksums file.
			f = open(filename)
			h = hashlib.sha512()
			while True:
				buf = f.read(BUFFER_SIZE)
				if not buf:
					break

				h.update(buf)
			f.close()

			chksums.write("%-10s %s\n" % (arcname, h.hexdigest()))

		# Close checksum file and attach it to the end.
		chksums.close()
		tar.add(chksumsfile, "chksums")

		# Close the tar file.
		tar.close()

	def add(self, filename, arcname=None):
		if not arcname:
			arcname = os.path.basename(filename)

		log.debug("Adding %s (as %s) to tarball." % (filename, arcname))
		self.files.append((arcname, filename))

	def create_package_format(self):
		filename = self.mktemp()

		f = open(filename, "w")
		f.write("%s\n" % PACKAGE_FORMAT)
		f.close()

		return filename

	def create_filelist(self, datafile):
		filelist = self.mktemp()

		f = open(filelist, "w")

		if self.payload_compression == "xz":
			datafile = InnerTarFileXz.open(datafile)
		else:
			datafile = InnerTarFile.open(datafile)

		while True:
			m = datafile.next()
			if not m:
				break

			log.debug("  %s %-8s %-8s %s %6s %s" % \
				(tarfile.filemode(m.mode), m.uname, m.gname,
				"%d-%02d-%02d %02d:%02d:%02d" % time.localtime(m.mtime)[:6],
				util.format_size(m.size), m.name))

			f.write("%(name)-40s %(type)1s %(size)-10d %(uname)-10s %(gname)-10s %(mode)-6d %(mtime)-12d" \
				% m.get_info(tarfile.ENCODING, "strict"))

			# Calculate SHA512 hash of regular files.
			if m.isreg():
				mobj = datafile.extractfile(m)
				h = hashlib.sha512()

				while True:
					buf = mobj.read(BUFFER_SIZE)
					if not buf:
						break
					h.update(buf)

				mobj.close()
				f.write(" %s" % h.hexdigest())
			else:
				f.write(" -")

			caps = m.pax_headers.get("PAKFIRE.capabilities", None)
			if caps:
				f.write(" %s" % caps)
			else:
				f.write(" -")

			f.write("\n")

		log.info("")

		datafile.close()
		f.close()

		return filelist

	def run(self):
		raise NotImplementedError

	def getsize(self, filename):
		if tarfile.is_tarfile(filename):
			return os.path.getsize(filename)

		size = 0
		f = lzma.LZMAFile(filename)

		while True:
			buf = f.read(BUFFER_SIZE)
			if not buf:
				break

			size += len(buf)
		f.close()

		return size


class BinaryPackager(Packager):
	payload_compression = "xz"

	def __init__(self, pakfire, pkg, builder, buildroot):
		Packager.__init__(self, pakfire, pkg)

		self.builder = builder
		self.buildroot = buildroot

	def create_metafile(self, datafile):
		info = collections.defaultdict(lambda: "")

		# Extract datafile in temporary directory and scan for dependencies.
		tmpdir = self.mktemp(directory=True)

		if self.payload_compression == "xz":
			tarfile = InnerTarFileXz.open(datafile)
		else:
			tarfile = InnerTarFile.open(datafile)

		tarfile.extractall(path=tmpdir)
		tarfile.close()

		# Run the dependency tracker.
		self.pkg.track_dependencies(self.builder, tmpdir)

		# Generic package information including Pakfire information.
		info.update({
			"pakfire_version" : PAKFIRE_VERSION,
			"uuid"            : self.pkg.uuid,
			"type"            : "binary",
		})

		# Include distribution information.
		info.update(self.pakfire.distro.info)
		info.update(self.pkg.info)

		# Update package information for string formatting.
		info.update({
			"groups"      : " ".join(self.pkg.groups),
			"prerequires" : "\n".join([PACKAGE_INFO_DEPENDENCY_LINE % d \
				for d in self.pkg.prerequires]),
			"requires"    : "\n".join([PACKAGE_INFO_DEPENDENCY_LINE % d \
				for d in self.pkg.requires]),
			"provides"    : "\n".join([PACKAGE_INFO_DEPENDENCY_LINE % d \
				for d in self.pkg.provides]),
			"conflicts"   : "\n".join([PACKAGE_INFO_DEPENDENCY_LINE % d \
				for d in self.pkg.conflicts]),
			"obsoletes"   : "\n".join([PACKAGE_INFO_DEPENDENCY_LINE % d \
				for d in self.pkg.obsoletes]),
		})

		# Format description.
		description = [PACKAGE_INFO_DESCRIPTION_LINE % l \
			for l in util.text_wrap(self.pkg.description, length=80)]
		info["description"] = "\n".join(description)

		# Build information.
		info.update({
			# Package it built right now.
			"build_time" : int(time.time()),
			"build_id"   : uuid.uuid4(),
		})

		# Installed size (equals size of the uncompressed tarball).
		info.update({
			"inst_size" : self.getsize(datafile),
		})

		metafile = self.mktemp()

		f = open(metafile, "w")
		f.write(PACKAGE_INFO % info)
		f.close()

		return metafile

	def create_datafile(self):
		includes = []
		excludes = []

		# List of all patterns, which grows.
		patterns = self.pkg.files

		for pattern in patterns:
			# Check if we are running in include or exclude mode.
			if pattern.startswith("!"):
				files = excludes

				# Strip the ! character.
				pattern = pattern[1:]
			else:
				files = includes

			# Expand file to point to chroot.
			if pattern.startswith("/"):
				pattern = pattern[1:]
			pattern = os.path.join(self.buildroot, pattern)

			# Recognize the type of the pattern. Patterns could be a glob
			# pattern that is expanded here or just a directory which will
			# be included recursively.
			if "*" in pattern or "?" in pattern or ("[" in pattern and "]" in pattern):
				_patterns = glob.glob(pattern)
			else:
				_patterns = [pattern,]

			for pattern in _patterns:
				# Try to stat the pattern. If that is not successful, we cannot go on.
				try:
					os.lstat(pattern)
				except OSError:
					continue

				# Add directories recursively but skip those symlinks
				# that point to a directory.
				if os.path.isdir(pattern) and not os.path.islink(pattern):
					# Add directory itself.
					files.append(pattern)

					for dir, subdirs, _files in os.walk(pattern):
						for subdir in subdirs:
							if subdir in ORPHAN_DIRECTORIES:
								continue

							subdir = os.path.join(dir, subdir)
							files.append(subdir)

						for file in _files:
							file = os.path.join(dir, file)
							files.append(file)

				# All other files are just added.
				else:
					files.append(pattern)

		# ...
		orphan_directories = [os.path.join(self.buildroot, d) for d in ORPHAN_DIRECTORIES]

		files = []
		for file in includes:
			# Skip if file is already in the file set or
			# marked to be excluded from this archive.
			if file in excludes or file in files:
				continue

			# Skip orphan directories.
			if file in orphan_directories and not os.listdir(file):
				log.debug("Found an orphaned directory: %s" % file)
				continue

			files.append(file)

			while True:
				file = os.path.dirname(file)

				if file == self.buildroot:
					break

				if not file in files:
					files.append(file)

		files.sort()

		# Load progressbar.
		message = "%-10s : %s" % (_("Packaging"), self.pkg.friendly_name)
		pb = util.make_progress(message, len(files), eta=False)

		datafile = self.mktemp()
		if self.payload_compression == "xz":
			tar = InnerTarFileXz.open(datafile, mode="w")
		else:
			tar = InnerTarFile.open(datafile, mode="w")

		# All files in the tarball are relative to this directory.
		basedir = self.buildroot

		i = 0
		for file in files:
			if pb:
				i += 1
				pb.update(i)

			# Never package /.
			if os.path.normpath(file) == os.path.normpath(basedir):
				continue

			# Name of the file in the archive.
			arcname = "/%s" % os.path.relpath(file, basedir)

			# Add file to tarball.
			tar.add(file, arcname=arcname, recursive=False)

		# Remove all packaged files.
		for file in reversed(files):
			# It's okay if we cannot remove directories,
			# when they are not empty.
			if os.path.isdir(file):
				try:
					os.rmdir(file)
				except OSError:
					continue
			else:
				try:
					os.unlink(file)
				except OSError:
					pass

			while True:
				file = os.path.dirname(file)

				if not file.startswith(basedir):
					break

				try:
					os.rmdir(file)
				except OSError:
					break

		# Close the tarfile.
		tar.close()

		# Finish progressbar.
		if pb:
			pb.finish()

		return datafile

	def create_scriptlets(self):
		scriptlets = []

		# Collect all prerequires for the scriptlets.
		prerequires = []

		for scriptlet_name in SCRIPTS:
			scriptlet = self.pkg.get_scriptlet(scriptlet_name)

			if not scriptlet:
				continue

			# Write script to a file.
			scriptlet_file = self.mktemp()

			lang = scriptlet["lang"]

			if lang == "bin":
				path = lang["path"]
				try:
					f = open(path, "b")
				except OSError:
					raise Exception, "Cannot open script file: %s" % lang["path"]

				s = open(scriptlet_file, "wb")

				while True:
					buf = f.read(BUFFER_SIZE)
					if not buf:
						break

					s.write(buf)

				f.close()
				s.close()

			elif lang == "shell":
				s = open(scriptlet_file, "w")

				# Write shell script to file.
				s.write("#!/bin/sh -e\n\n")
				s.write(scriptlet["scriptlet"])
				s.write("\n\nexit 0\n")
				s.close()

				if scriptlet_name in SCRIPTS_PREREQUIRES:
					# Shell scripts require a shell to be executed.
					prerequires.append("/bin/sh")

					prerequires += self.builder.find_prerequires(scriptlet_file)

			elif lang == "python":
				# Write the code to the scriptlet file.
				s = open(scriptlet_file, "w")
				s.write(scriptlet["scriptlet"])
				s.close()

			else:
				raise Exception, "Unknown scriptlet language: %s" % scriptlet["lang"]

			scriptlets.append((scriptlet_name, scriptlet_file))

		# Cleanup prerequires.
		self.pkg.update_prerequires(prerequires)

		return scriptlets

	def create_configs(self, datafile):
		if self.payload_compression == "xz":
			datafile = InnerTarFileXz.open(datafile)
		else:
			datafile = InnerTarFile.open(datafile)

		members = datafile.getmembers()

		configfiles = []
		configdirs  = []

		# Find all directories in the config file list.
		for file in self.pkg.configfiles:
			if file.startswith("/"):
				file = file[1:]

			for member in members:
				if member.name == file and member.isdir():
					configdirs.append(file)

		for configdir in configdirs:
			for member in members:
				if not member.isdir() and member.name.startswith(configdir):
					configfiles.append(member.name)

		for pattern in self.pkg.configfiles:
			if pattern.startswith("/"):
				pattern = pattern[1:]

			for member in members:
				if not fnmatch.fnmatch(member.name, pattern):
					continue

				if member.name in configfiles:
					continue

				configfiles.append(member.name)

		# Sort list alphabetically.
		configfiles.sort()

		configsfile = self.mktemp()

		f = open(configsfile, "w")
		for file in configfiles:
			f.write("%s\n" % file)
		f.close()

		return configsfile

	def run(self, resultdir):
		# Add all files to this package.
		datafile = self.create_datafile()

		# Get filelist from datafile.
		filelist = self.create_filelist(datafile)
		configs  = self.create_configs(datafile)

		# Create script files.
		scriptlets = self.create_scriptlets()

		metafile = self.create_metafile(datafile)

		# Add files to the tar archive in correct order.
		self.add(metafile, "info")
		self.add(filelist, "filelist")
		self.add(configs,  "configs")
		self.add(datafile, "data.img")

		for scriptlet_name, scriptlet_file in scriptlets:
			self.add(scriptlet_file, "scriptlets/%s" % scriptlet_name)

		# Build the final package.
		tempfile = self.mktemp()
		self.save(tempfile)

		# Add architecture information to path.
		resultdir = "%s/%s" % (resultdir, self.pkg.arch)

		if not os.path.exists(resultdir):
			os.makedirs(resultdir)

		resultfile = os.path.join(resultdir, self.pkg.package_filename)
		log.info("Saving package to %s" % resultfile)
		try:
			os.link(tempfile, resultfile)
		except OSError:
			shutil.copy2(tempfile, resultfile)

		return BinaryPackage(self.pakfire, self.pakfire.repos.dummy, resultfile)


class SourcePackager(Packager):
	payload_compression = None

	def create_metafile(self, datafile):
		info = collections.defaultdict(lambda: "")

		# Generic package information including Pakfire information.
		info.update({
			"pakfire_version" : PAKFIRE_VERSION,
			"type"            : "source",
		})

		# Include distribution information.
		info.update(self.pakfire.distro.info)
		info.update(self.pkg.info)

		# Size is the size of the (uncompressed) datafile.
		info["inst_size"] = self.getsize(datafile)

		# Update package information for string formatting.
		requires = [PACKAGE_INFO_DEPENDENCY_LINE % r for r in self.pkg.requires]
		info.update({
			"groups"   : " ".join(self.pkg.groups),
			"requires" : "\n".join(requires),
		})

		# Format description.
		description = [PACKAGE_INFO_DESCRIPTION_LINE % l \
			for l in util.text_wrap(self.pkg.description, length=80)]
		info["description"] = "\n".join(description)

		# Build information.
		info.update({
			# Package it built right now.
			"build_time" : int(time.time()),
			"build_id"   : uuid.uuid4(),
		})

		# Arches equals supported arches.
		info["arch"] = self.pkg.supported_arches

		# Set UUID
		# XXX replace this by the payload hash
		info.update({
			"uuid"       : uuid.uuid4(),
		})

		metafile = self.mktemp()

		f = open(metafile, "w")
		f.write(PACKAGE_INFO % info)
		f.close()

		return metafile

	def create_datafile(self):
		# Create a list of all files that have to be put into the
		# package.
		files = []

		# Download all files that go into the package.
		for file in self.pkg.download():
			assert os.path.getsize(file), "Don't package empty files"
			files.append(("files/%s" % os.path.basename(file), file))

		# Add all files in the package directory.
		for file in self.pkg.files:
			files.append((os.path.relpath(file, self.pkg.path), file))

		# Add files in alphabetical order.
		files.sort()

		# Load progressbar.
		message = "%-10s : %s" % (_("Packaging"), self.pkg.friendly_name)
		pb = util.make_progress(message, len(files), eta=False)

		filename = self.mktemp()
		if self.payload_compression == "xz":
			datafile = InnerTarFileXz.open(filename, mode="w")
		else:
			datafile = InnerTarFile.open(filename, mode="w")

		i = 0
		for arcname, file in files:
			if pb:
				i += 1
				pb.update(i)

			datafile.add(file, arcname)
		datafile.close()

		if pb:
			pb.finish()

		return filename

	def run(self, resultdir):
		# Create resultdir if it does not exist yet.
		if not os.path.exists(resultdir):
			os.makedirs(resultdir)

		log.info(_("Building source package %s:") % self.pkg.package_filename)

		# The filename where this source package is saved at.
		target_filename = os.path.join(resultdir, self.pkg.package_filename)

		# Add datafile to package.
		datafile = self.create_datafile()

		# Create filelist out of data.
		filelist = self.create_filelist(datafile)

		# Create metadata.
		metafile = self.create_metafile(datafile)

		# Add files to the tar archive in correct order.
		self.add(metafile, "info")
		self.add(filelist, "filelist")
		self.add(datafile, "data.img")

		# Build the final tarball.
		try:
			self.save(target_filename)
		except:
			# Remove the target file when anything went wrong.
			os.unlink(target_filename)
			raise

		return target_filename
