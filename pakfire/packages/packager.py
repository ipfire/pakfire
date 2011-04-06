#!/usr/bin/python

import glob
import logging
import lzma
import os
import progressbar
import re
import shutil
import sys
import tarfile
import tempfile
import uuid
import xattr
import zlib

import pakfire.compress
from pakfire.util import rm
import util

from pakfire.constants import *
from pakfire.i18n import _

from file import InnerTarFile

class Packager(object):
	ARCHIVE_FILES = ("info", "filelist", "data.img")

	def __init__(self, pakfire, pkg, env):
		self.pakfire = pakfire
		self.pkg = pkg
		self.env = env

		self.tarball = None

		self.cleanup = True

		# Store meta information
		self.info = {
			"package_format" : PACKAGE_FORMAT,
			"package_type" : self.type,
			"package_uuid" : uuid.uuid4(),
			"payload_comp" : "",

			"requires" : "",
			"provides" : "",
		}
		self.info.update(self.pkg.info)
		self.info["groups"] = " ".join(self.info["groups"])
		self.info.update(self.pakfire.distro.info)
		self.info.update(self.env.info)

		### Create temporary files
		# Create temp directory to where we extract all files again and
		# gather some information about them like requirements and provides.
		self.tempdir = self.env.chrootPath("tmp", "%s_data" % self.pkg.friendly_name)
		if not os.path.exists(self.tempdir):
			os.makedirs(self.tempdir)

		# Create files that have the archive data
		self.archive_files = {}
		for i in self.ARCHIVE_FILES:
			self.archive_files[i] = \
				self.env.chrootPath("tmp", "%s_%s" % (self.pkg.friendly_name, i))

	def __call__(self):
		logging.debug("Packaging %s" % self.pkg.friendly_name)

		# Create the tarball and add all data to it.
		self.create_tarball()

		if self.type == "binary":
			e = self.env.do("/usr/lib/buildsystem-tools/dependency-tracker %s" % \
				self.tempdir[len(self.env.chrootPath()):], returnOutput=True,
				env=self.pkg.env)

			for line in e.splitlines():
				m = re.match(r"^(\w+)=(.*)$", line)
				if m is None:
					continue

				key, val = m.groups()

				if not key in ("requires", "provides"):
					continue

				val = val.strip("\"")
				val = val.split()

				self.info[key] = " ".join(sorted(val))

		self.create_info()

		# Create the outer tarball.
		resultdir = os.path.join(self.env.chrootPath("result", self.pkg.arch))
		if not os.path.exists(resultdir):
			os.makedirs(resultdir)

		filename = os.path.join(resultdir, self.pkg.filename)

		tar = tarfile.TarFile(filename, mode="w", format=tarfile.PAX_FORMAT)

		for i in self.ARCHIVE_FILES:
			tar.add(self.archive_files[i], arcname=i)

		tar.close()

		rm(self.tempdir)

	def create_tarball(self, compress=None):
		tar = InnerTarFile(self.archive_files["data.img"], mode="w")

		prefix = self.env.buildroot
		if self.type == "source":
			prefix = "build"

		if not compress and self.type == "binary":
			compress = "xz"

		includes = []
		excludes = []

		for pattern in self.pkg.file_patterns:
			# Check if we are running in include or exclude mode.
			if pattern.startswith("!"):
				files = excludes

				# Strip the ! charater
				pattern = pattern[1:]

			else:
				files = includes

			if pattern.startswith("/"):
				pattern = pattern[1:]
			pattern = self.env.chrootPath(prefix, pattern)

			# Recognize the type of the pattern. Patterns could be a glob
			# pattern that is expanded here or just a directory which will
			# be included recursively.
			if "*" in pattern or "?" in pattern:
				files += glob.glob(pattern)

			elif os.path.exists(pattern):
				# Add directories recursively...
				if os.path.isdir(pattern):
					for dir, subdirs, _files in os.walk(pattern):
						for file in _files:
							file = os.path.join(dir, file)
							files.append(file)

				# all other files are just added.
				else:
					files.append(pattern)

		files = []
		for file in includes:
			# Skip if file is already in the file set or
			# marked to be excluded from this archive.
			if file in excludes or file in files:
				continue

			files.append(file)

		files.sort()

		filelist = open(self.archive_files["filelist"], mode="w")

		for file_real in files:
			file_tar = file_real[len(self.env.chrootPath(prefix)) + 1:]
			file_tmp = os.path.join(self.tempdir, file_tar)

			if file_tar in ORPHAN_DIRECTORIES and not os.listdir(file_real):
				logging.debug("Found an orphaned directory: %s" % file_tar)
				os.unlink(file_real)
				continue

			tar.add(file_real, arcname=file_tar)

			# Record the packaged file to the filelist.
			filelist.write("/%s\n" % file_tar)

			# "Copy" the file to the tmp path for later investigation.
			if os.path.isdir(file_real):
				file_dir = file_tmp
			else:
				file_dir = os.path.dirname(file_tmp)

			if not os.path.exists(file_dir):
				os.makedirs(file_dir)

			if os.path.isfile(file_real):
				os.link(file_real, file_tmp)

			elif os.path.islink(file_real):
				# Dead symlinks cannot be copied by shutil.
				os.symlink(os.readlink(file_real), file_tmp)

			elif os.path.isdir(file_real):
				if not os.path.exists(file_tmp):
					os.makedirs(file_tmp)

			else:
				shutil.copy2(file_real, file_tmp)

			# Unlink the file and remove empty directories.
			if self.cleanup:
				if not os.path.isdir(file_real):
					os.unlink(file_real)

				elif os.path.isdir(file_real) and not os.listdir(file_real):
					os.rmdir(file_real)

		# Dump all files that are in the archive.
		tar.list()

		# Write all data to disk.
		tar.close()
		filelist.close()

		# compress the tarball here
		if compress:
			# Save algorithm to metadata.
			self.info["payload_comp"] = compress

			logging.debug("Compressing package with %s algorithm." % compress or "no")

			# Compress file (in place).
			pakfire.compress.compress(self.archive_files["data.img"],
				algo=compress, progress=True)

		# Calc hashsum of the payload of the package.
		self.info["payload_hash1"] = util.calc_hash1(self.archive_files["data.img"])

	def create_info(self):
		f = open(self.archive_files["info"], "w")
		f.write(BINARY_PACKAGE_META % self.info)
		f.close()

	@property
	def type(self):
		raise NotImplementedError


class BinaryPackager(Packager):
	@property
	def type(self):
		return "binary"


class SourcePackager(Packager):
	def __init__(self, *args, **kwargs):
		Packager.__init__(self, *args, **kwargs)

		self.cleanup = False

	@property
	def type(self):
		return "source"
