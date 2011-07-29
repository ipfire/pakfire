#!/usr/bin/python

from file import FilePackage

class SourcePackage(FilePackage):
	@property
	def arch(self):
		return "src"
