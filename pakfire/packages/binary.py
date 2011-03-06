#!/usr/bin/python

import sys

import packager

from file import FilePackage

class BinaryPackage(FilePackage):
	type = "bin"

	@property
	def arch(self):
		return self.metadata.get("PKG_ARCH")

	@property
	def requires(self):
		ret = ""

		for i in ("PKG_REQUIRES", "PKG_DEPS"):
			ret = self.metadata.get(i, ret)
			if ret:
				break

		return ret.split()

	@property
	def provides(self):
		if not hasattr(self, "__provides"):
			# Get automatic provides
			provides = self._provides

			# Add other provides
			for prov in self.metadata.get("PKG_PROVIDES", "").split():
				if not prov in provides:
					provides.append(prov)

			self.__provides = provides

		return self.__provides

	@property
	def conflicts(self):
		return self.metadata.get("PKG_CONFLICTS", "").split()

	@property
	def obsoletes(self):
		return self.metadata.get("PKG_OBSOLETES", "").split()

	def get_extractor(self, pakfire):
		return packager.Extractor(pakfire, self)

