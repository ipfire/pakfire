#!/usr/bin/python

import sys

from file import FilePackage

class BinaryPackage(FilePackage):
	@property
	def arch(self):
		return self.metadata.get("PKG_ARCH")

	@property
	def provides(self):
		if not hasattr(self, "__provides"):
			# Get automatic provides
			provides = self._provides

			# Add other provides
			for prov in self.metadata.get("PKG_PROVIDES", "").split():
				provides.add(prov)

			self.__provides = provides

		return self.__provides

	@property
	def conflicts(self):
		conflicts = self.metadata.get("PKG_CONFLICTS", "").split()

		return set(conflicts)

	@property
	def obsoletes(self):
		obsoletes = self.metadata.get("PKG_OBSOLETES", "").split()

		return set(obsoletes)

