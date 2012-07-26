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

import tarfile

TYPE_REG  = tarfile.REGTYPE	# regular file
TYPE_AREG = tarfile.AREGTYPE	# regular file
TYPE_LNK  = tarfile.LNKTYPE	# link (inside tarfile)
TYPE_SYM  = tarfile.SYMTYPE	# symbolic link
TYPE_CHR  = tarfile.CHRTYPE	# character special device
TYPE_BLK  = tarfile.BLKTYPE	# block special device
TYPE_DIR  = tarfile.DIRTYPE	# directory
TYPE_FIFO = tarfile.FIFOTYPE	# fifo special device
TYPE_CONT = tarfile.CONTTYPE	# contiguous file

TYPE_DIR_INT = int(TYPE_DIR)

class _File(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

	def __cmp__(self, other):
		ret = cmp(self.name, other.name)

		if not ret:
			ret = cmp(self.pkg, other.pkg)

		return ret

	def is_dir(self):
		# XXX TODO
		# VERY POOR CHECK
		return self.name.endswith("/")

	def is_config(self):
		# XXX TODO
		return False


class File(_File):
	def __init__(self, pakfire):
		_File.__init__(self, pakfire)

		self.name = ""
		self.config = False
		self.pkg  = None
		self.size = -1
		self.hash1 = None
		self.type = TYPE_REG
		self.mode = 0
		self.user = 0
		self.group = 0
		self.mtime = 0
		self.capabilities = None

	def is_dir(self):
		return self.type == TYPE_DIR_INT \
			or self.name.endswith("/")

	def is_config(self):
		return self.config


class FileDatabase(_File):
	def __init__(self, pakfire, db, row_id, row=None):
		_File.__init__(self, pakfire)

		self.db = db
		self.row_id = row_id
		self.__row = row

	@property
	def row(self):
		"""
			Lazy fetching of the database row.
		"""
		if self.__row is None:
			c = self.db.cursor()
			c.execute("SELECT * FROM files WHERE id = ? LIMIT 1", (self.row_id,))

			self.__row = c.fetchone()
			c.close()

		return self.__row

	def is_dir(self):
		return self.type == TYPE_DIR_INT \
			or self.name.endswith("/")

	def is_config(self):
		return self.row["config"] == 1

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

	@property
	def type(self):
		return self.row["type"]

	@property
	def mode(self):
		return self.row["mode"]

	@property
	def user(self):
		return self.row["user"]

	@property
	def group(self):
		return self.row["group"]

	@property
	def mtime(self):
		return self.row["mtime"]

	@property
	def capabilities(self):
		return self.row["capabilities"]
