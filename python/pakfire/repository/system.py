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

import base
import database

class RepositorySystem(base.RepositoryFactory):
	def __init__(self, pakfire):
		base.RepositoryFactory.__init__(self, pakfire, "@system", "Local repository")

		# Open database connection.
		self.db = database.DatabaseLocal(self.pakfire, self)

		# Tell the solver, that these are the installed packages.
		self.pool.set_installed(self.solver_repo)

	@property
	def priority(self):
		"""
			The local repository has always a high priority.
		"""
		return 10

	def update(self, force=False, offline=False):
		if not force:
			force = len(self) == 0

		if force:
			self.index.clear()
			for pkg in self.db.packages:
				self.index.add_package(pkg)

	def commit(self):
		# Commit the database to disk.
		self.db.commit()

	def add_package(self, pkg):
		# Add package to the database.
		self.db.add_package(pkg)
		self.index.add_package(pkg)

	def rem_package(self, pkg):
		# Remove package from the database.
		self.index.rem_package(pkg)

	@property
	def filelist(self):
		# XXX ugly?

		for pkg in self.db.packages:
			for file in pkg.filelist:
				yield file
