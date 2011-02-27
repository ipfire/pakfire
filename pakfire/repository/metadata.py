#!/usr/bin/python

import json
import time

from pakfire.constants import *

class Metadata(object):
	def __init__(self, pakfire, index, metafile=None, metadata=None):
		self.pakfire = pakfire
		self.index = index

		self.filename = metafile

		# Place where we save the data.
		self._data = {
			"database" : None,
			"revision" : int(time.time()),
			"version"  : METADATA_FORMAT,
		}

		# If a file was passed, we open it.
		if self.filename:
			self.open()

		# ... or parse the one that was passed.
		elif metadata:
			self.parse(metadata)

	def __cmp__(self, other):
		"""
			Compare two sets of metadata by their revision.
		"""
		return cmp(self.revision, other.revision)

	def parse(self, metadata):
		try:
			self._data = json.loads(metadata)
		except:
			raise # XXX catch json exceptions here

	def open(self, filename=None):
		"""
			Open a given file or use the default one and parse the
			data in it.
		"""
		if not filename:
			filename = self.filename

		with open(filename) as f:
			self.parse(f.read())

	def save(self, filename=None):
		"""
			Save all data to a file that could be exported to a
			remote repository.
		"""
		if not filename:
			filename = self.filename

		f = open(filename, "w")

		# Write all data to the fileobj.
		json.dump(self._data, f, indent=2)

		f.close()

	@property
	def version(self):
		"""
			Returns the version of the metadata.
		"""
		return self._data.get("version")

	@property
	def revision(self):
		"""
			Returns the revision of the metadata.
		"""
		return self._data.get("revision")

	def get_database(self):
		return self._data.get("database")

	def set_database(self, val):
		self._data["database"] = val

	database = property(get_database, set_database)

	def get_database_hash1(self):
		return self._data.get("database_hash1", None)

	def set_database_hash1(self, val):
		self._data["database_hash1"] = val

	database_hash1 = property(get_database_hash1, set_database_hash1)

	def get_database_compression(self):
		return self._data.get("database_compression", None)

	def set_database_compression(self, val):
		self._data["database_compression"] = val

	database_compression = property(get_database_compression,
		set_database_compression)
