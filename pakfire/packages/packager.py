#!/usr/bin/python

import glob
import logging
import lzma
import os
import progressbar
import shutil
import sys
import tarfile
import tempfile
import uuid
import xattr
import zlib

from pakfire.constants import *
from pakfire.i18n import _

class Extractor(object):
	def __init__(self, pakfire, pkg):
		self.pakfire = pakfire
		self.pkg = pkg

		self.data = pkg.get_file("data.img")

		self.archive = None
		self._tempfile = None

		if self.pkg.payload_compression:
			self.uncompress_payload()
		else:
			self.archive = tarfile.open(fileobj=self.data)

	def cleanup(self):
		# XXX not called by anything
		if self._tempfile:
			os.unlink(self._tempfile)

	def uncompress_payload(self):
		# XXX this function uncompresses the data.img file
		# and saves the bare tarball to /tmp which takes a lot
		# of space.

		# Create a temporary file to save the content in
		f, self._tempfile = tempfile.mkstemp()
		f = open(self._tempfile, "w")

		if self.pkg.payload_compression == "xz":
			decompressor = lzma.LZMADecompressor()

		elif self.pkg.payload_compression == "zlib":
			decompressor = zlib.decompressobj()

		buf = self.data.read(BUFFER_SIZE)
		while buf:
			f.write(decompressor.decompress(buf))

			buf = self.data.read(BUFFER_SIZE)

		f.write(decompressor.flush())
		f.close()

		self.archive = tarfile.open(self._tempfile)

	@property
	def files(self):
		return self.archive.getnames()

	def extractall(self, path="/", callback=None):
		pbar = self._make_progressbar()

		if pbar:
			pbar.start()
		else:
			print "  %s %-20s" % (_("Extracting"), self.pkg.name)

		i = 0
		for name in self.files:
			i += 1
			self.extract(name, path, callback=callback)

			if pbar:
				pbar.update(i)

		if pbar:
			pbar.finish()
			#sys.stdout.write("\n")

	def extract(self, filename, path="/", callback=None):
		member = self.archive.getmember(filename)
		target = os.path.join(path, filename)

		# If the member is a directory and if it already exists, we
		# don't need to create it again.
		if member.isdir() and os.path.exists(target):
			return

		#if self.pakfire.config.get("debug"):
		#	msg = "Creating file (%s:%03d:%03d) " % \
		#		(tarfile.filemode(member.mode), member.uid, member.gid)
		#	if member.issym():
		#		msg += "/%s -> %s" % (member.name, member.linkname)
		#	elif member.islnk():
		#		msg += "/%s link to /%s" % (member.name, member.linkname)
		#	else:
		#		msg += "/%s" % member.name
		#	logging.debug(msg)

		# Remove file if it has been existant
		if not member.isdir() and os.path.exists(target):
			os.unlink(target)

		self.archive.extract(member, path=path)

		# XXX implement setting of xattrs/acls here

		if callback and not member.isdir():
			callback(member.name, hash1="XXX", size=member.size)

	def _make_progressbar(self):
		# Don't display a progressbar if we are running in debug mode.
		if self.pakfire.config.get("debug"):
			return

		if not sys.stdout.isatty():
			return

		widgets = [
			"  ",
			"%s %-20s" % (_("Extracting:"), self.pkg.name),
			" ",
			progressbar.Bar(left="[", right="]"),
			"  ",
#			progressbar.Percentage(),
#			"  ",
			progressbar.ETA(),
			"  ",
		]

		# maxval must be > 0 and so we assume that
		# empty packages have at least one file.
		maxval = len(self.files) or 1

		return progressbar.ProgressBar(
			widgets=widgets,
			maxval=maxval,
			term_width=80,
		)


class InnerTarFile(tarfile.TarFile):
	def __init__(self, *args, **kwargs):
		# Force the pax format
		kwargs["format"] = tarfile.PAX_FORMAT

		if kwargs.has_key("env"):
			self.env = kwargs.pop("env")

		tarfile.TarFile.__init__(self, *args, **kwargs)

	def __filter_xattrs(self, tarinfo):
		logging.debug("Adding file: %s" % tarinfo.name)

		filename = self.env.chrootPath(self.env.buildroot, tarinfo.name)

		# xattrs do only exists for regular files. If we don't have one,
		# simply skip.
		if os.path.isfile(filename):
			for attr, value in xattr.get_all(filename):
				tarinfo.pax_headers[attr] = value

				logging.debug("  xattr: %s=%s" % (attr, value))

		return tarinfo

	def add(self, *args, **kwargs):
		# Add filter for xattrs if no other filter is set.
		if not kwargs.has_key("filter") and len(args) < 5:
			kwargs["filter"] = self.__filter_xattrs

		tarfile.TarFile.add(self, *args, **kwargs)


# XXX this is totally ugly and needs to be done right!

class Packager(object):
	ARCHIVE_FILES = ("info", "filelist", "data.img")

	def __init__(self, pakfire, pkg, env):
		self.pakfire = pakfire
		self.pkg = pkg
		self.env = env

		self.tarball = None

		# Store meta information
		self.info = {
			"package_format" : PACKAGE_FORMAT,
			"package_uuid" : uuid.uuid4(),
			"payload_comp" : None,
		}
		self.info.update(self.pkg.info)
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

		chroot_tempdir = self.tempdir[len(self.env.chrootPath()):]
		self.info.update({
			"requires" : self.env.do("/usr/lib/buildsystem-tools/dependency-tracker requires %s" % chroot_tempdir,
				returnOutput=True, env=self.pkg.env).strip(),
			"provides" : self.env.do("/usr/lib/buildsystem-tools/dependency-tracker provides %s" % chroot_tempdir,
				returnOutput=True, env=self.pkg.env).strip(),
		})

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

	def create_tarball(self, compress="xz"):
		tar = InnerTarFile(self.archive_files["data.img"], mode="w", env=self.env)

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
			pattern = self.env.chrootPath(self.env.buildroot, pattern)

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

			else:
				logging.warning("Unrecognized pattern type: %s" % pattern)

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
			file_tar = file_real[len(self.env.chrootPath(self.env.buildroot)) + 1:]
			file_tmp = os.path.join(self.tempdir, file_tar)

			tar.add(file_real, arcname=file_tar, recursive=False)

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

			else:
				shutil.copy2(file_real, file_tmp)

			# Unlink the file and remove empty directories.
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

			filename = self.archive_files["data.img"]
			i = open(filename)
			os.unlink(filename)

			o = open(filename, "w")

			if compress == "xz":
				comp = lzma.LZMACompressor()

			elif compress == "zlib":
				comp = zlib.compressobj(9)

			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(comp.compress(buf))

				buf = i.read(BUFFER_SIZE)

			o.write(comp.flush())

			i.close()
			o.close()

	def create_info(self):
		f = open(self.archive_files["info"], "w")
		f.write(BINARY_PACKAGE_META % self.info)
		f.close()
