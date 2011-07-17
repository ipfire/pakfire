#!/usr/bin/python

import fnmatch
import glob
import logging
import re

import cache
import pakfire.satsolver as satsolver

class RepositoryFactory(object):
	def __init__(self, pakfire, name, description):
		self.pakfire = pakfire
		self.name = name
		self.description = description

		# Reference to corresponding Repo object in the solver.
		self.solver_repo = satsolver.Repo(self.pool, self.name)

		logging.debug("Initialized new repository: %s" % self)

		# Create an cache object
		self.cache = cache.RepositoryCache(self.pakfire, self)

		# The index MUST be set by an inheriting class.
		self.index = None

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __cmp__(self, other):
		return cmp(self.priority * -1, other.priority * -1) or \
			cmp(self.name, other.name)

	def __len__(self):
		return self.solver_repo.size()

	@property
	def pool(self):
		return self.pakfire.pool

	def get_enabled(self):
		return self.solver_repo.get_enabled()

	def set_enabled(self, val):
		self.solver_repo.set_enabled(val)

		if val:
			logging.debug("Enabled repository '%s'." % self.name)
		else:
			logging.debug("Disabled repository '%s'." % self.name)

	enabled = property(get_enabled, set_enabled)

	@property
	def arch(self):
		return self.pakfire.distro.arch

	@property
	def distro(self):
		"""
			Link to distro object.
		"""
		return self.pakfire.distro

	@property
	def priority(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Say if a repository is a local one or remotely located.

			Used to check if we need to download files.
		"""
		return False

	def update(self, force=False):
		"""
			A function that is called to update the local data of
			the repository.
		"""
		assert self.index

		self.index.update(force)


class RepositoryDummy(RepositoryFactory):
	"""
		Just a dummy repository that actually does nothing.
	"""
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "dummy",
			"This is a dummy repository.")
