#!/usr/bin/python

import index

from base import RepositoryFactory

class InstalledRepository(RepositoryFactory):
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "installed", "Installed packages")

		self.index = index.InstalledIndex(self.pakfire, self)

	@property
	def local(self):
		# This is obviously local.
		return True

	@property
	def priority(self):
		"""
			The installed repository has always the highest priority.
		"""
		return 0
