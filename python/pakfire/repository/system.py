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

import os

import base
import database

import pakfire.packages as packages
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class RepositorySystem(base.RepositoryFactory):
	def __init__(self, pakfire):
		base.RepositoryFactory.__init__(self, pakfire, "@system", "Local repository")

		# Open database connection.
		self.db = database.DatabaseLocal(self.pakfire, self)

		# Tell the solver, that these are the installed packages.
		self.pool.set_installed(self.solver_repo)

	@property
	def cache_file(self):
		return os.path.join(self.pakfire.path, PACKAGES_SOLV)

	@property
	def priority(self):
		"""
			The local repository has always a high priority.
		"""
		return 10

	def open(self):
		# Initialize database.
		self.db.initialize()

		# Create a progressbar.
		pb = util.make_progress(_("Loading installed packages"), len(self.db))

		# Remove all data from the current index.
		self.index.clear()

		i = 0
		for pkg in self.db.packages:
			if pb:
				i += 1
				pb.update(i)

			self.index.add_package(pkg)

		self.index.optimize()

		if pb:
			pb.finish()

		# Mark repo as open.
		self.opened = True

	def close(self):
		# Commit all data that is currently pending for writing.
		self.db.commit()

		# Close database.
		self.db.close()

		# Remove indexed data from memory.
		self.index.clear()

		# Mark repo as closed.
		self.opened = False

	def commit(self):
		# Commit the database to disk.
		self.db.commit()

		# Make sure that all data in the index is accessable.
		self.index.optimize()

		# Write the content of the index to a file
		# for fast parsing.
		# XXX this is currently disabled
		#self.index.write(self.cache_file)

	def add_package(self, pkg):
		# Add package to the database.
		self.db.add_package(pkg)
		self.index.add_package(pkg)

	def rem_package(self, pkg):
		assert isinstance(pkg, packages.SolvPackage), pkg

		# Remove package from the database.
		self.db.rem_package(pkg)
		self.index.rem_package(pkg)

	@property
	def filelist(self):
		return self.db.get_filelist()
