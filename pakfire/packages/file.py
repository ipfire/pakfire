#!/usr/bin/python

import logging
import os
import re
import tarfile
import xattr

import util

from pakfire.errors import FileError

from base import Package

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
			attrs = xattr.get_all(name)

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
		# Extract file the normal way...
		tarfile.TarFile.extract(self, member, path)

		# ...and then apply the extended attributes.
		if member.pax_headers:
			target = os.path.join(path, member.name)

			for attr, val in member.pax_headers.items():
				# Skip all attrs that are not supported (e.g. selinux).
				if not attr in self.SUPPORTED_XATTRS:
					continue

				logging.debug("Restoring xattr %s=%s to %s" % (attr, val, target))
				xattr.set(target, attr, val)


class FilePackage(Package):
	"""
		This class is a wrapper that reads package data from the (outer)
		tarball and should never be used solely.
	"""
	def __init__(self, pakfire, repo, filename):
		Package.__init__(self, pakfire, repo)
		self.filename = filename

		# Place to cache the metadata
		self._metadata = {}

		self.check()

	def check(self):
		"""
			Initially check if the given file is of the correct type and
			can be opened.
		"""
		if not tarfile.is_tarfile(self.filename):
			raise FileError, "Given file is not of correct format: %s" % self.filename

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.filename)

	@property
	def local(self):
		# A file package is always local.
		return True

	def open_archive(self):
		return tarfile.open(self.filename)

	@property
	def file_version(self):
		"""
			Returns the version of the package metadata.
		"""
		return self.metadata.get("VERSION")

	@property
	def metadata(self):
		"""
			Read-in the metadata from the "info" file and cache it in _metadata.
		"""
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

	def __filelist_from_metadata(self):
		a = self.open_archive()
		f = a.extractfile("filelist")

		ret = []
		for line in f.readlines():
			line = line.strip()
			if not line.startswith("/"):
				line = "/%s" % line

			ret.append(line)

		f.close()
		a.close()

		return ret

	def __filelist_from_payload(self):
		# XXX expect uncompressed payload for now
		# this is very simple and very slow

		a = self.open_archive()
		f = a.extractfile("data.img")
		t = tarfile.open(fileobj=f)

		ret = ["/%s" % n for n in t.getnames()]

		t.close()
		f.close()
		a.close()

		return ret

	@property
	def filelist(self):
		"""
			Return a list of the files that are contained in the package
			payload.

			At first, we try to get them from the metadata (which is the
			'filelist' file).
			If the file is not existant, we will open the payload and
			read it instead. The latter is a very slow procedure and
			should not be used anyway.
		"""
		if not hasattr(self, "__filelist"):
			try:
				self.__filelist = self.__filelist_from_metadata()
			except KeyError:
				self.__filelist = self.__filelist_from_payload()

		return self.__filelist

	@property
	def payload_compression(self):
		"""
			Return the compression type of the payload.
		"""
		comp = self.metadata.get("PKG_PAYLOAD_COMP", None)

		# Remove triple X placeholder that was used some time.
		if comp == "X"*3:
			comp = None

		# XXX remove that later, because of compatibility for naoki.
		elif not comp:
			comp = "xz"

		return comp

	@property
	def signature(self):
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
	def scriptlet(self):
		"""
			Read the scriptlet from the archive or return an empty string if no
			scriptlet does exist.
		"""
		ret = None
		try:
			a = self.open_archive()
			f = a.extractfile("control")

			ret = f.read()

			f.close()
			a.close()

		except KeyError:
			# scriptlet file could not be found
			pass

		return ret or ""
