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
import logging
import lzma
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

import pakfire.compress
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

from file import BinaryPackage, InnerTarFile, SourcePackage

class Packager(object):
	def __init__(self, pakfire, pkg):
		self.pakfire = pakfire
		self.pkg = pkg

		self.files = []
		self.tmpfiles = []

	def __del__(self):
		for file in self.tmpfiles:
			if not os.path.exists(file):
				continue

			logging.debug("Removing tmpfile: %s" % file)

			if os.path.isdir(file):
				util.rm(file)
			else:
				os.remove(file)

	def mktemp(self, directory=False):
		# XXX use real mk(s)temp here
		filename = os.path.join("/", LOCAL_TMP_PATH, util.random_string())

		if directory:
			os.makedirs(filename)

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

		logging.debug("Adding %s (as %s) to tarball." % (filename, arcname))
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
		datafile = InnerTarFile(datafile)

		for m in datafile.getmembers():
			logging.debug("  %s %-8s %-8s %s %6s %s" % \
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

		logging.info("")

		datafile.close()
		f.close()

		return filelist

	def run(self):
		raise NotImplementedError


class BinaryPackager(Packager):
	def __init__(self, pakfire, pkg, builder, buildroot):
		Packager.__init__(self, pakfire, pkg)

		self.builder = builder
		self.buildroot = buildroot

	def create_metafile(self, datafile):
		info = collections.defaultdict(lambda: "")

		# Extract datafile in temporary directory and scan for dependencies.
		tmpdir = self.mktemp(directory=True)

		tarfile = InnerTarFile(datafile)
		tarfile.extractall(path=tmpdir)
		tarfile.close()

		# Run the dependency tracker.
		self.pkg.track_dependencies(self.builder, tmpdir)

		# Generic package information including Pakfire information.
		info.update({
			"pakfire_version" : PAKFIRE_VERSION,
			"uuid"            : uuid.uuid4(),
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
			"inst_size" : os.path.getsize(datafile),
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
				if not os.path.exists(pattern):
					continue

				# Add directories recursively...
				if os.path.isdir(pattern):
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

				# all other files are just added.
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
				logging.debug("Found an orphaned directory: %s" % file)
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
		tar = InnerTarFile(datafile, mode="w")

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

		for scriptlet_name in SCRIPTS:
			scriptlet = self.pkg.get_scriptlet(scriptlet_name)

			if not scriptlet:
				continue

			# Write script to a file.
			scriptlet_file = self.mktemp()

			if scriptlet["lang"] == "bin":
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

			elif scriptlet["lang"] == "shell":
				s = open(scriptlet_file, "w")

				# Write shell script to file.
				s.write("#!/bin/sh -e\n\n")
				s.write(scriptlet["scriptlet"])
				s.write("\n\nexit 0\n")

				s.close()

			else:
				raise Exception, "Unknown scriptlet language: %s" % scriptlet["lang"]

			scriptlets.append((scriptlet_name, scriptlet_file))

		# XXX scan for script dependencies

		return scriptlets

	def create_configs(self, datafile):
		datafile = InnerTarFile(datafile)

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

	def compress_datafile(self, datafile, algo="xz"):
		outputfile = self.mktemp()

		# Compress the datafile with the choosen algorithm.
		pakfire.compress.compress_file(datafile, outputfile, algo=algo,
			progress=True, message=_("Compressing %s") % self.pkg.friendly_name)

		# We do not need the uncompressed output anymore.
		os.unlink(datafile)

		# The outputfile becomes out new datafile.
		return outputfile

	def run(self, resultdir):
		# Add all files to this package.
		datafile = self.create_datafile()

		# Get filelist from datafile.
		filelist = self.create_filelist(datafile)
		configs  = self.create_configs(datafile)

		# Create script files.
		scriptlets = self.create_scriptlets()

		metafile = self.create_metafile(datafile)

		# XXX make xz in variable
		datafile = self.compress_datafile(datafile, algo="xz")

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
		logging.info("Saving package to %s" % resultfile)
		try:
			os.link(tempfile, resultfile)
		except OSError:
			shutil.copy2(tempfile, resultfile)

		return BinaryPackage(self.pakfire, self.pakfire.repos.dummy, resultfile)


class SourcePackager(Packager):
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
		info["inst_size"] = os.path.getsize(datafile)

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
		filename = self.mktemp()
		datafile = InnerTarFile(filename, mode="w")

		# Add all downloaded files to the package.
		for file in self.pkg.download():
			datafile.add(file, "files/%s" % os.path.basename(file))

		# Add all files in the package directory.
		for file in sorted(self.pkg.files):
			arcname = os.path.relpath(file, self.pkg.path)
			datafile.add(file, arcname)

		datafile.close()

		return filename

	def run(self, resultdirs=[]):
		assert resultdirs

		logging.info(_("Building source package %s:") % self.pkg.package_filename)

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
		tempfile = self.mktemp()
		self.save(tempfile)

		for resultdir in resultdirs:
			# XXX sometimes, there has been a None in resultdirs
			if not resultdir:
				continue

			resultdir = "%s/%s" % (resultdir, self.pkg.arch)

			if not os.path.exists(resultdir):
				os.makedirs(resultdir)

			resultfile = os.path.join(resultdir, self.pkg.package_filename)
			logging.info("Saving package to %s" % resultfile)
			try:
				os.link(tempfile, resultfile)
			except OSError:
				shutil.copy2(tempfile, resultfile)

		# Dump package information.
		pkg = SourcePackage(self.pakfire, self.pakfire.repos.dummy, tempfile)
		for line in pkg.dump(long=True).splitlines():
			logging.info(line)
		logging.info("")
