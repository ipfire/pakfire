#!/usr/bin/python

from file import FilePackage

class BinaryPackage(FilePackage):
	@property
	def arch(self):
		return self.metadata.get("PKG_ARCH")
