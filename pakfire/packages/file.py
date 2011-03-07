#!/usr/bin/python

import tarfile
import os
import re

import util

from pakfire.errors import FileError

from base import Package

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
