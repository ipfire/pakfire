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
import tarfile
import tempfile
import xattr

import pakfire.filelist
import pakfire.util as util
import pakfire.compress as compress
from pakfire.constants import *
from pakfire.i18n import _

from base import Package
from lexer import FileLexer

# XXX need to add zlib and stuff here.
PAYLOAD_COMPRESSION_MAGIC = {
	"xz" : "\xfd7zXZ",
}

class InnerTarFile(tarfile.TarFile):
	SUPPORTED_XATTRS = ("security.capability",)

	def __init__(self, *args, **kwargs):
		# Force the PAX format.
		kwargs["format"] = tarfile.PAX_FORMAT

		tarfile.TarFile.__init__(self, *args, **kwargs)

	def add(self, name, arcname=None, recursive=None, exclude=None, filter=None):
		"""
			Emulate the add function with xattrs support.
		"""
		tarinfo = self.gettarinfo(name, arcname)

		if tarinfo.isreg():
			attrs = []

			# Use new modules code...
			if hasattr(xattr, "get_all"):
				attrs = xattr.get_all(name)

			# ...or use the deprecated API.
			else:
				for attr in xattr.listxattr(name):
					val = xattr.getxattr(name, attr)
					attrs.append((attr, val))

			for attr, val in attrs:
				# Skip all attrs that are not supported (e.g. selinux).
				if not attr in self.SUPPORTED_XATTRS:
					continue

				logging.debug("Saving xattr %s=%s from %s" % (attr, val, name))

				tarinfo.pax_headers[attr] = val

	        # Append the tar header and data to the archive.
			f = tarfile.bltn_open(name, "rb")
			self.addfile(tarinfo, f)
			f.close()

		elif tarinfo.isdir():
			self.addfile(tarinfo)
			if recursive:
				for f in os.listdir(name):
					self.add(os.path.join(name, f), os.path.join(arcname, f),
							recursive, exclude, filter)

		else:
			self.addfile(tarinfo)

	def extract(self, member, path=""):
		target = os.path.join(path, member.name)

		# Remove symlink targets, because tarfile cannot replace them.
		if member.issym() and os.path.exists(target):
			print "unlinking", target
			os.unlink(target)

		# Extract file the normal way...
		try:
			tarfile.TarFile.extract(self, member, path)
		except OSError, e:
			logging.warning(_("Could not extract file: /%(src)s - %(dst)s") \
				% { "src" : member.name, "dst" : e, })

		# ...and then apply the extended attributes.
		if member.pax_headers:
			for attr, val in member.pax_headers.items():
				# Skip all attrs that are not supported (e.g. selinux).
				if not attr in self.SUPPORTED_XATTRS:
					continue

				logging.debug("Restoring xattr %s=%s to %s" % (attr, val, target))
				if hasattr(xattr, "set"):
					xattr.set(target, attr, val)

				else:
					xattr.setxattr(target, attr, val)


class FilePackage(Package):
	"""
		This class is a wrapper that reads package data from the (outer)
		tarball and should never be used solely.
	"""
	def __init__(self, pakfire, repo, filename):
		Package.__init__(self, pakfire, repo)
		self.filename = os.path.abspath(filename)

		# Place to cache the metadata
		self._metadata = {}

		# Place to cache the filelist
		self._filelist = None

		# Store the format of this package file.
		self.format = self.get_format()

		# XXX need to make this much better.
		self.check()

		# Read the info file.
		if self.format >= 1:
			a = self.open_archive()
			f = a.extractfile("info")

			self.lexer = FileLexer(f.readlines())

			f.close()
			a.close()

		elif self.format == 0:
			pass

		else:
			raise PackageFormatUnsupportedError, _("Filename: %s") % self.filename

	def check(self):
		"""
			Initially check if the given file is of the correct type and
			can be opened.
		"""
		if not tarfile.is_tarfile(self.filename):
			raise FileError, "Given file is not of correct format: %s" % self.filename

		assert self.format in PACKAGE_FORMATS_SUPPORTED

	def get_format(self):
		a = self.open_archive()
		try:
			f = a.extractfile("pakfire-format")
		except KeyError:
			return 0

		format = f.read()
		try:
			format = int(format)
		except TypeError:
			format = 0

		f.close()
		a.close()

		return format

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.filename)

	@property
	def local(self):
		# A file package is always local.
		return True

	def open_archive(self):
		return tarfile.open(self.filename, format=tarfile.PAX_FORMAT)

	def extract(self, message=None, prefix=None):
		logging.debug("Extracting package %s" % self.friendly_name)

		if prefix is None:
			prefix = ""

		# A place to store temporary data.
		tempf = None

		# Open package data for read.
		archive = self.open_archive()

		# Get the package payload.
		payload = archive.extractfile("data.img")

		# Decompress the payload if needed.
		logging.debug("Compression: %s" % self.payload_compression)

		# Create a temporary file to store the decompressed output.
		garbage, tempf = tempfile.mkstemp(prefix="pakfire")

		i = payload
		o = open(tempf, "w")

		# Decompress the package payload.
		if self.payload_compression:
			compress.decompressobj(i, o, algo=self.payload_compression)

		else:
			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(buf)
				buf = i.read(BUFFER_SIZE)

		i.close()
		o.close()

		payload = open(tempf)

		# Open the tarball in the package.
		payload_archive = InnerTarFile.open(fileobj=payload)

		members = payload_archive.getmembers()

		# Load progressbar.
		pb = None
		if message:
			message = "%-10s : %s" % (message, self.friendly_name)
			pb = util.make_progress(message, len(members), eta=False)

		i = 0
		for member in members:
			# Update progress.
			if pb:
				i += 1
				pb.update(i)

			target = os.path.join(prefix, member.name)

			# If the member is a directory and if it already exists, we
			# don't need to create it again.

			if os.path.exists(target):
				if member.isdir():
					continue

				else:
					# Remove file if it has been existant
					os.unlink(target)

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

			payload_archive.extract(member, path=prefix)

		# Close all open files.
		payload_archive.close()
		payload.close()
		archive.close()

		if tempf:
			os.unlink(tempf)

		if pb:
			pb.finish()

	@property
	def metadata(self):
		"""
			Read-in the metadata from the "info" file and cache it in _metadata.
		"""
		assert self.format == 0, self

		if not self._metadata:
			a = self.open_archive()
			f = a.extractfile("info")

			for line in f.readlines():
				m = re.match(r"^(\w+)=(.*)$", line)
				if m is None:
					continue

				key, val = m.groups()
				self._metadata[key] = val.strip("\"")

			f.close()
			a.close()

		return self._metadata

	@property
	def size(self):
		"""
			Return the size of the package file.
		"""
		return os.path.getsize(self.filename)

	@property
	def inst_size(self):
		inst_size = 0

		if self.format >= 1:
			inst_size = self.lexer.package.get_var("size")
			try:
				inst_size = int(inst_size)
			except TypeError:
				inst_size = 0

		return inst_size

	def get_filelist(self):
		"""
			Return a list of the files that are contained in the package
			payload.
		"""
		ret = []

		a = self.open_archive()
		f = a.extractfile("filelist")

		for line in f.readlines():
			line = line.strip()

			file = pakfire.filelist.File(self.pakfire)

			if self.format >= 1:
				line = line.split()
				name = line[0]

				# XXX need to parse the rest of the information from the
				# file

			else:
				name = line

			if not name.startswith("/"):
				name = "/%s" % name

			file.name = name
			file.pkg  = self

			ret.append(file)

		f.close()
		a.close()

		return ret

	@property
	def filelist(self):
		if self._filelist is None:
			self._filelist = self.get_filelist()

		return self._filelist

	@property
	def configfiles(self):
		a = self.open_archive()

		f = a.extractfile("configs")
		for line in f.readlines():
			if not line.startswith("/"):
				line = "/%s" % line
			yield line

		a.close()

	@property
	def payload_compression(self):
		"""
			Return the (guessed) compression type of the payload.
		"""
		# Get the max. length of the magic values.
		max_length = max([len(v) for v in PAYLOAD_COMPRESSION_MAGIC.values()])

		a = self.open_archive()
		f = a.extractfile("data.img")

		# Read magic bytes from file.
		magic = f.read(max_length)

		f.close()
		a.close()

		for algo, m in PAYLOAD_COMPRESSION_MAGIC.items():
			if not magic.startswith(m):
				continue

			return algo

	@property
	def signature(self):
		# XXX needs to be replaced
		"""
			Read the signature from the archive or return None if no
			signature does exist.
		"""
		ret = None
		try:
			a = self.open_archive()
			f = a.extractfile("signature")

			ret = f.read()

			f.close()
			a.close()

		except KeyError:
			# signature file could not be found
			pass

		return ret or None

	@property
	def hash1(self):
		"""
			Calculate the hash1 of this package.
		"""
		return util.calc_hash1(self.filename)
	
	@property
	def name(self):
		if self.format >= 1:
			name = self.lexer.package.get_var("name")
		elif self.format == 0:
			name = self.metadata.get("PKG_NAME")

		assert name, self
		return name

	@property
	def epoch(self):
		if self.format >= 1:
			epoch = self.lexer.package.get_var("epoch", 0)
		elif self.format == 0:
			epoch = self.metadata.get("PKG_EPOCH")

		try:
			epoch = int(epoch)
		except TypeError:
			epoch = 0

		return epoch

	@property
	def version(self):
		if self.format >= 1:
			version = self.lexer.package.get_var("version")
		elif self.format == 0:
			version = self.metadata.get("PKG_VER")

		assert version, self
		return version

	@property
	def release(self):
		if self.format >= 1:
			release = self.lexer.package.get_var("release")
		elif self.format == 0:
			release = self.metadata.get("PKG_REL")

		assert release, self
		return release

	@property
	def arch(self):
		if self.format >= 1:
			arch = self.lexer.package.get_var("arch")
		elif self.format == 0:
			arch = self.metadata.get("PKG_ARCH")

		assert arch, self
		return arch

	@property
	def vendor(self):
		if self.format >= 1:
			vendor = self.lexer.distro.get_var("vendor")
		elif self.format == 0:
			vendor = self.metadata.get("PKG_VENDOR")

		return vendor

	@property
	def summary(self):
		if self.format >= 1:
			summary = self.lexer.package.get_var("summary")
		elif self.format == 0:
			summary = self.metadata.get("PKG_SUMMARY")

		assert summary, self
		return summary

	@property
	def description(self):
		if self.format >= 1:
			description = self.lexer.package.get_var("description")
		elif self.format == 0:
			description = self.metadata.get("PKG_DESC")

		return description

	@property
	def groups(self):
		if self.format >= 1:
			groups = self.lexer.package.get_var("groups")
		elif self.format == 0:
			groups = self.metadata.get("PKG_GROUPS")

		if groups:
			return groups.split()

		return []

	@property
	def license(self):
		if self.format >= 1:
			license = self.lexer.package.get_var("license")
		elif self.format == 0:
			license = self.metadata.get("PKG_LICENSE")

		return license

	@property
	def url(self):
		if self.format >= 1:
			url = self.lexer.package.get_var("url")
		elif self.format == 0:
			url = self.metadata.get("PKG_URL")

		return url

	@property
	def maintainer(self):
		if self.format >= 1:
			maintainer = self.lexer.package.get_var("maintainer")
		elif self.format == 0:
			maintainer = self.metadata.get("PKG_MAINTAINER")

		return maintainer

	@property
	def uuid(self):
		if self.format >= 1:
			uuid = self.lexer.package.get_var("uuid")
		elif self.format == 0:
			uuid = self.metadata.get("PKG_UUID")

		#assert uuid, self XXX re-enable this
		return uuid

	@property
	def build_id(self):
		if self.format >= 1:
			build_id = self.lexer.build.get_var("id")
		elif self.format == 0:
			build_id = self.metadata.get("BUILD_ID")

		assert build_id, self
		return build_id

	@property
	def build_host(self):
		if self.format >= 1:
			build_host = self.lexer.build.get_var("host")
		elif self.format == 0:
			build_host = self.metadata.get("BUILD_HOST")

		assert build_host, self
		return build_host

	@property
	def build_time(self):
		if self.format >= 1:
			build_time = self.lexer.build.get_var("time")
		elif self.format == 0:
			build_time = self.metadata.get("BUILD_TIME")

		# XXX re-enable this later
		#assert build_time, self

		try:
			build_time = int(build_time)
		except TypeError:
			build_time = 0

		return build_time

	@property
	def provides(self):
		if self.format >= 1:
			provides = self.lexer.deps.get_var("provides")
		elif self.format == 0:
			provides = self.metadata.get("PKG_PROVIDES")

		if not provides:
			return []

		return provides.split()

	@property
	def requires(self):
		if self.format >= 1:
			requires = self.lexer.deps.get_var("requires")
		elif self.format == 0:
			requires = self.metadata.get("PKG_REQUIRES")

		if not requires:
			return []

		return requires.split()

	@property
	def prerequires(self):
		if self.format >= 1:
			prerequires = self.lexer.deps.get_var("prerequires")
		elif self.format == 0:
			prerequires = self.metadata.get("PKG_PREREQUIRES")

		if not prerequires:
			return []

		return prerequires.split()

	@property
	def obsoletes(self):
		if self.format >= 1:
			obsoletes = self.lexer.deps.get_var("obsoletes")
		elif self.format == 0:
			obsoletes = self.metadata.get("PKG_OBSOLETES")

		if not obsoletes:
			return []

		return obsoletes.split()

	@property
	def conflicts(self):
		if self.format >= 1:
			conflicts = self.lexer.deps.get_var("conflicts")
		elif self.format == 0:
			conflicts = self.metadata.get("PKG_CONFLICTS")

		if not conflicts:
			return []

		return conflicts.split()


class SourcePackage(FilePackage):
	pass


class BinaryPackage(FilePackage):
	def get_scriptlet(self, type):
		a = self.open_archive()

		# Path of the scriptlet in the tarball.
		path = "scriptlets/%s" % type

		try:
			f = a.extractfile(path)
		except KeyError:
			# If the scriptlet is not available, we just return.
			return

		scriptlet = f.read()

		f.close()
		a.close()

		return scriptlet
