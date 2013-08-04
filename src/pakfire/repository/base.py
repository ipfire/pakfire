#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import logging
log = logging.getLogger("pakfire")

import index

import pakfire.packages as packages
import pakfire.satsolver as satsolver

class RepositoryFactory(object):
	def __init__(self, pakfire, name, description):
		self.pakfire = pakfire
		self.name = name
		self.description = description

		# Reference to corresponding Repo object in the solver.
		self.solver_repo = satsolver.Repo(self.pool, self.name)
		self.solver_repo.set_priority(self.priority)

		# Some repositories may have a cache.
		self.cache = None

		log.debug("Initialized new repository: %s" % self)

		# Create an index (in memory).
		self.index = index.Index(self.pakfire, self)

		# Marks if this repository has been opened.
		self.opened = False

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __cmp__(self, other):
		return cmp(self.priority * -1, other.priority * -1) or \
			cmp(self.name, other.name)

	def __len__(self):
		return self.solver_repo.size()

	def __iter__(self):
		pkgs = []

		for solv in self.solver_repo.get_all():
			pkg = packages.SolvPackage(self.pakfire, solv, self)
			pkgs.append(pkg)

		return iter(pkgs)

	@property
	def pool(self):
		return self.pakfire.pool

	def get_enabled(self):
		return self.solver_repo.get_enabled()

	def set_enabled(self, val):
		self.solver_repo.set_enabled(val)

		if val:
			log.debug("Enabled repository '%s'." % self.name)
		else:
			log.debug("Disabled repository '%s'." % self.name)

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

	def open(self):
		"""
			Opens the repository, so we can work with the data.
		"""
		self.opened = True

	def close(self):
		"""
			Close and delete all resources that are used by this repository.
		"""
		self.opened = False

	def clean(self):
		"""
			Cleanup all temporary files of this repository.
		"""
		log.info("Cleaning up repository '%s'..." % self.name)

		# Clear all packages in the index.
		self.index.clear()

	def dump(self, long=False, filelist=False):
		dumps = []
		# Dump all package information of the packages in this repository.
		for pkg in self:
			dump = pkg.dump(long=long, filelist=filelist)
			dumps.append(dump)

		return "\n\n".join(dumps)

	def get_config(self):
		"""
			Return the configuration as a list of string which
			can be written to a configuration file.
		"""
		pass


class RepositoryDummy(RepositoryFactory):
	"""
		Just a dummy repository that actually does nothing.
	"""
	def __init__(self, pakfire):
		RepositoryFactory.__init__(self, pakfire, "dummy",
			"This is a dummy repository.")

	@property
	def priority(self):
		# This will never be used in the solving process, but still it needs
		# a value.
		return 0
