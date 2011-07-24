#!/usr/bin/python

from file import FilePackage

class SourcePackage(FilePackage):
	@property
	def arch(self):
		return "src"

	@property
	def requires(self):
		"""
			Return the requirements for the build.
		"""
		return self.metadata.get("PKG_REQUIRES", "").split()

	@property
	def conflicts(self):
		return self.metadata.get("PKG_CONFLICTS", "").split()
