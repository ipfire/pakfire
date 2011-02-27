#!/usr/bin/python

from base import RepositoryFactory

class DummyRepository(RepositoryFactory):
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

