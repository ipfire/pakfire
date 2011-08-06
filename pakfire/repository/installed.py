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
