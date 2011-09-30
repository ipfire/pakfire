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

class _File(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire


class File(_File):
	def __init__(self, pakfire):
		_File.__init__(self, pakfire)

		self.name = ""
		self.pkg  = None
		self.size = -1
		self.hash1 = ""

	def __cmp__(self, other):
		return cmp(self.pkg, other.pkg) or cmp(self.name, other.name)

	def is_dir(self):
		# XXX TODO
		# VERY POOR CHECK
		return self.name.endswith("/")

	def is_config(self):
		# XXX TODO
		return False


class FileDatabase(_File):
	def __init__(self, pakfire, db, row_id):
		_File.__init__(self, pakfire)

		self.db = db
		self.row_id = row_id

		self.__row = None

	@property
	def row(self):
		"""
			Lazy fetching of the database row.
		"""
		if self.__row is None:
			c = self.db.cursor()
			c.execute("SELECT * FROM files WHERE id = ? LIMIT 1", (self.row_id,))

			# Check if we got the same row.
			#assert c.lastrowid == self.row_id

			for row in c:
				self.__row = row
				break

			c.close()

		return self.__row

	@property
	def pkg(self):
		return self.db.get_package_by_id(self.row["pkg"])

	@property
	def name(self):
		return self.row["name"]

	@property
	def size(self):
		return self.row["size"]

	@property
	def hash1(self):
		return self.row["hash1"]
