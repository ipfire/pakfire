#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2012 Pakfire development team                                 #
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
import tarfile

import logging
log = logging.getLogger("pakfire")

import pakfire.lzma as lzma
import pakfire.util as util
from pakfire.constants import *
from pakfire.i18n import _

class InnerTarFile(tarfile.TarFile):
	def __init__(self, *args, **kwargs):
		# Force the PAX format.
		kwargs["format"] = tarfile.PAX_FORMAT

		tarfile.TarFile.__init__(self, *args, **kwargs)

	def add(self, name, arcname=None, recursive=None, exclude=None, filter=None):
		"""
			Emulate the add function with capability support.
		"""
		tarinfo = self.gettarinfo(name, arcname)

		if tarinfo.isreg():
			attrs = []

			# Save capabilities.
			caps = util.get_capabilities(name)
			if caps:
				log.debug("Saving capabilities for %s: %s" % (name, caps))
				tarinfo.pax_headers["PAKFIRE.capabilities"] = caps

			# Append the tar header and data to the archive.
			f = tarfile.bltn_open(name, "rb")
			self.addfile(tarinfo, f)
			f.close()

		elif tarinfo.isdir():
			self.addfile(tarinfo)
			if recursive:
				for f in os.listdir(name):
					self.add(os.path.join(name, f), os.path.join(arcname, f),
							recursive, exclude, filter)

		else:
			self.addfile(tarinfo)

		# Return the tar information about the file
		return tarinfo

	def extract(self, member, path=""):
		target = os.path.join(path, member.name)

		# Remove symlink targets, because tarfile cannot replace them.
		if member.issym():
			try:
				os.unlink(target)
			except OSError:
				pass

		# Extract file the normal way...
		try:
			tarfile.TarFile.extract(self, member, path)
		except OSError, e:
			log.warning(_("Could not extract file: /%(src)s - %(dst)s") \
				% { "src" : member.name, "dst" : e, })

		if path:
			target = os.path.join(path, member.name)
		else:
			target = "/%s" % member.name

		# ...and then apply the capabilities.
		caps = member.pax_headers.get("PAKFIRE.capabilities", None)
		if caps:
			log.debug("Restoring capabilities for /%s: %s" % (member.name, caps))
			util.set_capabilities(target, caps)


class InnerTarFileXz(InnerTarFile):
	@classmethod
	def open(cls, name=None, mode="r", fileobj=None, **kwargs):
		fileobj = lzma.LZMAFile(name, mode, fileobj=fileobj)

		try:
			t = cls.taropen(name, mode, fileobj, **kwargs)
		except lzma.LZMAError:
			fileobj.close()
			raise tarfile.ReadError("not an lzma file")

		t._extfileobj = False
		return t
