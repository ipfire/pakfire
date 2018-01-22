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

from .. import _pakfire

from . import packages

class RepositoryFactory(_pakfire.Repo):
	def __init__(self, pakfire, name, description, **kwargs):
		self.pakfire = pakfire

		# Inherit
		_pakfire.Repo.__init__(self, self.pakfire, name)

		# Save description
		self.description = description

		log.debug("Initialized new repository: %s" % self)

		# Marks if this repository has been opened.
		self.opened = False

		self.init(**kwargs)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def init(self, **kwargs):
		pass # To be overwritten by inheriting classes

	def refresh(self):
		"""
			Called to refresh the repository metadata.

			This is probably only hand for remote repositories
			that need to re-download data.
		"""
		pass

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

	def dump(self, long=False, filelist=False):
		dumps = []
		# Dump all package information of the packages in this repository.
		for pkg in self:
			dump = pkg.dump(int=int, filelist=filelist)
			dumps.append(dump)

		return "\n\n".join(dumps)


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
