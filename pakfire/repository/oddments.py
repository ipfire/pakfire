#!/usr/bin/python

from base import RepositoryFactory

class RepositoryDummy(RepositoryFactory):
	"""
		Just a dummy repository that actually does nothing.
	"""
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "dummy",
			"This is a dummy repository.")


class FileSystemRepository(RepositoryFactory):
	"""
		Dummy repository to indicate that a specific package came from the
		filesystem.
	"""
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "filesystem",
			"Filesystem repository")

	@property
	def priority(self):
		# Has always the highest priority because it has packages
		# the user passed on the command line and really wants to get
		# installed.
		return 0
