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

import hashlib
import os
import re
import shutil
import tarfile
import tempfile

import logging
log = logging.getLogger("pakfire")

import pakfire.filelist
import pakfire.lzma as lzma
import pakfire.util as util
import pakfire.compress as compress
from pakfire.constants import *
from pakfire.i18n import _

from base import Package
from lexer import FileLexer

class InnerTarFile(tarfile.TarFile):
	def __init__(self, *args, **kwargs):
		# Force the PAX format.
		kwargs["format"] = tarfile.PAX_FORMAT

		tarfile.TarFile.__init__(self, *args, **kwargs)

	def add(self, name, arcname=None, recursive=None, exclude=None, filter=None):
		"""
			Emulate the add function with capability support.
		"""
		tarinfo = self.gettarinfo(name, arcname)

		if tarinfo.isreg():
			attrs = []

			# Save capabilities.
			caps = util.get_capabilities(name)
			if caps:
				log.debug("Saving capabilities for %s: %s" % (name, caps))
				tarinfo.pax_headers["PAKFIRE.capabilities"] = caps

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
		if member.issym():
			try:
				os.unlink(target)
			except OSError:
				pass

		# Extract file the normal way...
		try:
			tarfile.TarFile.extract(self, member, path)
		except OSError, e:
			log.warning(_("Could not extract file: /%(src)s - %(dst)s") \
				% { "src" : member.name, "dst" : e, })

		if path:
			target = os.path.join(path, member.name)
		else:
			target = "/%s" % member.name

		# ...and then apply the capabilities.
		caps = member.pax_headers.get("PAKFIRE.capabilities", None)
		if caps:
			log.debug("Restoring capabilities for /%s: %s" % (member.name, caps))
			util.set_capabilities(target, caps)


class InnerTarFileXz(InnerTarFile):
	@classmethod
	def open(cls, name=None, mode="r", fileobj=None, **kwargs):
		fileobj = lzma.LZMAFile(name, mode, fileobj=fileobj)

		try:
			t = cls.taropen(name, mode, fileobj, **kwargs)
		except lzma.LZMAError:
			fileobj.close()
			raise tarfile.ReadError("not an lzma file")

		t._extfileobj = False
		return t


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

		# Place to cache the filelist and payload compression algorithm.
		self._filelist = None
		self.__payload_compression = None

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

		assert self.format in PACKAGE_FORMATS_SUPPORTED, self.format

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

	def open_archive(self, mode="r"):
		return tarfile.open(self.filename, mode=mode, format=tarfile.PAX_FORMAT)

	def extract(self, message=None, prefix=None):
		log.debug("Extracting package %s" % self.friendly_name)

		if prefix is None:
			prefix = ""

		# Open package data for read.
		archive = self.open_archive()

		# Get the package payload.
		payload = archive.extractfile("data.img")

		# Decompress the payload if needed.
		if self.payload_compression == "xz":
			payload_archive = InnerTarFileXz.open(fileobj=payload)

		elif self.payload_compression == "none":
			payload_archive = InnerTarFile.open(fileobj=payload)

		else:
			raise Exception, "Unhandled payload compression type: %s" \
				% payload_compression

		# Load progressbar.
		pb = None
		if message:
			message = "%-10s : %s" % (message, self.friendly_name)
			pb = util.make_progress(message, len(self.filelist), eta=False)

		# Collect messages with errors and warnings, that are passed to
		# the user.
		messages = []

		name2file = {}
		for file in self.filelist:
			if file.is_dir() and file.name.endswith("/"):
				name = file.name[:-1]
			else:
				name = file.name

			name2file[name] = file

		i = 0
		while True:
			member = payload_archive.next()
			if not member:
				break

			# Check if file is also known in metadata.
			name = member.name
			if not name.startswith("/"):
				name = "/%s" % name

			try:
				file = name2file[name]
			except KeyError:
				log.warning(_("File in archive is missing in file metadata: %s. Skipping.") % name)
				continue

			# Update progress.
			if pb:
				i += 1
				pb.update(i)

			target = os.path.join(prefix, member.name)

			# Check if a configuration file is already present. We don't want to
			# overwrite that.
			if file.is_config():
				config_save = "%s%s" % (target, CONFIG_FILE_SUFFIX_SAVE)
				config_new  = "%s%s" % (target, CONFIG_FILE_SUFFIX_NEW)

				if os.path.exists(config_save) and not os.path.exists(target):
					# Extract new configuration file, save it as CONFIG_FILE_SUFFIX_NEW,
					# and reuse _SAVE.
					payload_archive.extract(member, path=prefix)

					shutil.move(target, config_new)
					shutil.move(config_save, target)
					continue

				elif os.path.exists(target):
					# If the files are identical, we skip the extraction of a
					# new configuration file. We also do that when the new configuration file
					# is a dummy file.
					if file.size == 0:
						continue

					# Calc hash of the current configuration file.
					config_hash1 = hashlib.sha512()
					f = open(target)
					while True:
						buf = f.read(BUFFER_SIZE)
						if not buf:
							break
						config_hash1.update(buf)
					f.close()

					if file.hash1 == config_hash1.hexdigest():
						continue

					# Backup old configuration file and extract new one.
					shutil.move(target, config_save)
					payload_archive.extract(member, path=prefix)

					# Save new configuration file as CONFIG_FILE_SUFFIX_NEW and
					# restore old configuration file.
					shutil.move(target, config_new)
					shutil.move(config_save, target)

					if prefix:
						config_new = os.path.relpath(config_new, prefix)
					messages.append(_("Config file created as %s") % config_new)
					continue

			# If the member is a directory and if it already exists, we
			# don't need to create it again.
			if os.path.exists(target):
				if member.isdir():
					continue

				else:
					# Remove file if it has been existant
					try:
						os.unlink(target)
					except OSError:
						messages.append(_("Could not remove file: /%s") % member.name)

			#if self.pakfire.config.get("debug"):
			#	msg = "Creating file (%s:%03d:%03d) " % \
			#		(tarfile.filemode(member.mode), member.uid, member.gid)
			#	if member.issym():
			#		msg += "/%s -> %s" % (member.name, member.linkname)
			#	elif member.islnk():
			#		msg += "/%s link to /%s" % (member.name, member.linkname)
			#	else:
			#		msg += "/%s" % member.name
			#	log.debug(msg)

			payload_archive.extract(member, path=prefix)

		# Close all open files.
		payload_archive.close()
		payload.close()
		archive.close()

		if pb:
			pb.finish()

		# Print messages.
		for msg in messages:
			log.warning(msg)

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

		# Cache configfiles.
		configfiles = []

		try:
			f = a.extractfile("configs")
			for line in f.readlines():
				line = line.rstrip()
				if not line.startswith("/"):
					line = "/%s" % line
				configfiles.append(line)
			f.close()
		except KeyError:
			pass # Package has no configuration files. Never mind.

		f = a.extractfile("filelist")
		for line in f.readlines():
			line = line.strip()

			file = pakfire.filelist.File(self.pakfire)

			if self.format >= 1:
				line = line.split(None, 8)

				# Check if fields do have the correct length.
				if self.format >= 3 and len(line) <= 7:
					continue
				elif len(line) <= 6:
					continue

				# Switch the first and last argument in the line.
				if self.format < 4:
					line.append(line.pop(0))

				name = line[-1]

				if not name.startswith("/"):
					name = "/%s" % name

				# Check if configfiles.
				if name in configfiles:
					file.config = True

				# Parse file type.
				try:
					file.type = int(line[0])
				except ValueError:
					file.type = 0

				# Parse the size information.
				try:
					file.size = int(line[1])
				except ValueError:
					file.size = 0

				# Parse user and group.
				file.user, file.group = line[2], line[3]

				# Parse mode.
				try:
					file.mode = int(line[4])
				except ValueError:
					file.mode = 0

				# Parse time.
				try:
					file.mtime = line[5]
				except ValueError:
					file.mtime = 0

				# Parse hash1 (sha512).
				if not line[6] == "-":
					file.hash1 = line[6]

				if self.format >= 3 and len(line) >= 9 and not line[7] == "-":
					file.capabilities = line[7]

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
		return [f for f in self.filelist if f.is_config()]

	@property
	def payload_compression(self):
		"""
			Return the (guessed) compression type of the payload.
		"""
		# We cache that because this is costly.
		if self.__payload_compression is None:
			a = self.open_archive()
			f = a.extractfile("data.img")

			# Go and guess what we do have here.
			self.__payload_compression = compress.guess_algo(fileobj=f)

			f.close()
			a.close()

		return self.__payload_compression or "none"

	### SIGNATURE STUFF

	@property
	def signatures(self):
		"""
			Read the signatures from the archive.
		"""
		ret = {}

		# Open the archive for reading.
		a = self.open_archive()

		for member in a.getmembers():
			# Skip all files that are not a signature.
			if not member.name.startswith("signatures/"):
				continue

			# Get the ID of the key.
			key_id = os.path.basename(member.name)

			# Get the content of the signature file.
			f = a.extractfile(member.name)
			signature = f.read()
			f.close()

			if signature:
				ret[key_id] = signature

		# Close the archive.
		a.close()

		return ret

	def has_signature(self, key_id):
		"""
			Check if the file a signature of the given key.
		"""
		return self.signatures.has_key(key_id)

	def __has_hardlinks(self):
		"""
			Returns True when a file has a hardlink.
		"""
		res = os.stat(self.filename)

		return res.st_nlink > 1

	def __remove_hardlinks(self):
		"""
			Remove all hardlinks from this file that we can alter it in place.
		"""
		if not self.__has_hardlinks():
			return

		# Open a file descriptor to the old file and remove the link from
		# the filesystem.
		f = open(self.filename, "rb")
		os.unlink(self.filename)

		# Create a new file with the exact same name for copying the data
		# to.
		g = open(self.filename, "wb")

		# Copy the data.
		while True:
			buf = f.read(BUFFER_SIZE)
			if not buf:
				break

			g.write(buf)

		# Close all files.
		f.close()
		g.close()

		# Make sure the whole process above worked fine.
		assert self.__has_hardlinks() is False

	def sign(self, key_id):
		"""
			Sign the package with the given key.
		"""
		# First check if the package has already been signed with this key.
		# If true, we do not have anything to do here.
		if self.has_signature(key_id):
			return False

		# Remove all hardlinks.
		self.__remove_hardlinks()

		# XXX verify the content of the file here.

		# Open the archive and read the checksum file.
		a = self.open_archive()

		f = a.extractfile("chksums")
		cleartext = f.read()

		f.close()
		a.close()

		# Create the signature.
		signature = self.pakfire.keyring.sign(key_id, cleartext)

		try:
			# Write the signature to a temporary file.
			f = tempfile.NamedTemporaryFile(mode="w", delete=False)
			f.write(signature)
			f.close()

			# Reopen the outer tarfile in write mode and append
			# the new signature.
			a = self.open_archive("a")
			a.add(f.name, "signatures/%s" % key_id)
			a.close()

		finally:
			os.unlink(f.name)

		return True

	def verify(self):
		"""
			Verify the tarball against the given key.

			If not key is given, only the checksums are compared to
			the actual data.
		"""

		# XXX replace Exception

		# Read the data of the checksum file.
		a = self.open_archive()
		f = a.extractfile("chksums")
		chksums = f.read()
		f.close()
		a.close()

		sigs = []
		for signature in self.signatures.values():
			sigs += self.pakfire.keyring.verify(signature, chksums)

		# Open the archive to access all files we will need.
		a = self.open_archive()

		# Read the chksums file.
		chksums = {}
		f = a.extractfile("chksums")
		for line in f.readlines():
			filename, chksum = line.split()
			chksums[filename] = chksum
		f.close()
		a.close()

		for filename, chksum in chksums.items():
			ret = self.check_chksum(filename, chksum)

			if ret:
				log.debug("Checksum of %s matches." % filename)
				continue
			else:
				log.debug("Checksum of %s does not match." % filename)

			raise Exception, "Checksum does not match: %s" % filename

		return sigs

	def check_chksum(self, filename, chksum, algo="sha512"):
		a = self.open_archive()
		f = a.extractfile(filename)

		h = hashlib.new(algo)
		while True:
			buf = f.read(BUFFER_SIZE)
			if not buf:
				break

			h.update(buf)

		f.close()
		a.close()

		return h.hexdigest() == chksum

	@property
	def hash1(self):
		"""
			Calculate the hash1 of this package.
		"""
		return util.calc_hash1(self.filename)

	@property
	def type(self):
		if self.format >= 2:
			type = self.lexer.package.get_var("type")
		elif self.format == 1:
			type = self._type
		else:
			type = self.metadata.get("type")

		assert type, self
		return type

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

		assert uuid, self
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

		provides = provides.splitlines()
		return self.filter_deps(provides)

	@property
	def requires(self):
		if self.format >= 1:
			requires = self.lexer.deps.get_var("requires")
		elif self.format == 0:
			requires = self.metadata.get("PKG_REQUIRES")

		if not requires:
			return []

		requires = requires.splitlines()
		return self.filter_deps(requires)

	@property
	def prerequires(self):
		if self.format >= 1:
			prerequires = self.lexer.deps.get_var("prerequires")
		elif self.format == 0:
			prerequires = self.metadata.get("PKG_PREREQUIRES")

		if not prerequires:
			return []

		prerequires = prerequires.splitlines()
		return self.filter_deps(prerequires)

	@property
	def obsoletes(self):
		if self.format >= 1:
			obsoletes = self.lexer.deps.get_var("obsoletes")
		elif self.format == 0:
			obsoletes = self.metadata.get("PKG_OBSOLETES")

		if not obsoletes:
			return []

		obsoletes = obsoletes.splitlines()
		return self.filter_deps(obsoletes)

	@property
	def conflicts(self):
		if self.format >= 1:
			conflicts = self.lexer.deps.get_var("conflicts")
		elif self.format == 0:
			conflicts = self.metadata.get("PKG_CONFLICTS")

		if not conflicts:
			return []

		conflicts = conflicts.splitlines()
		return self.filter_deps(conflicts)


class SourcePackage(FilePackage):
	_type = "source"

	@property
	def arch(self):
		return "src"

	@property
	def supported_arches(self):
		if self.format >= 2:
			arches = self.lexer.package.get_var("arch", "all")
		elif self.format == 1:
			# Format 1 did not support "supported_arches", so we assume "all".
			arches = "all"
		else:
			arches = self.metadata.get("PKG_SUPPORTED_ARCHES", "all")

		assert arches, self
		return arches


class BinaryPackage(FilePackage):
	_type = "binary"

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
