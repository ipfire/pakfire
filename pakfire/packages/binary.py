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
		return self.metadata.get("PKG_PROVIDES").split()

	def get_extractor(self, pakfire):
		return packager.Extractor(pakfire, self)

