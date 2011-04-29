#!/usr/bin/python

from file import FilePackage

class BinaryPackage(FilePackage):
	@property
	def arch(self):
		return self.metadata.get("PKG_ARCH")

	@property
	def conflicts(self):
		conflicts = self.metadata.get("PKG_CONFLICTS", "").split()

		return set(conflicts)

	@property
	def obsoletes(self):
		obsoletes = self.metadata.get("PKG_OBSOLETES", "").split()

		return set(obsoletes)

