#!/usr/bin/python

from base import Package

from pakfire.constants import *


class VirtualPackage(Package):
	def __init__(self, pakfire, data):
		self.pakfire = pakfire
		self._data = {}

		for key in data.keys():
			self._data[key] = data[key]

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.friendly_name)

	@property
	def metadata(self):
		return self._data

	@property
	def filename(self):
		return PACKAGE_FILENAME_FMT % {
			"arch"    : self.arch,
			"ext"     : PACKAGE_EXTENSION,
			"name"    : self.name,
			"release" : self.release,
			"version" : self.version,
		}

	@property
	def arch(self):
		return self.metadata.get("PKG_ARCH")

	@property
	def file_patterns(self):
		return self.metadata.get("PKG_FILES").split()

	@property
	def env(self):
		return self.metadata

