#!/usr/bin/python3
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

import lzma

from .constants import *
from .i18n import _

ALGO_DEFAULT = "xz"

# A dictionary with all compression types
# we do support.
# XXX add bzip2, and more here.
MAGICS = {
	#"gzip"  : "\037\213\010",
	"xz"    : "\xfd7zXZ",
}

FILES = {
	"xz"    : lzma.LZMAFile,
}

COMPRESSORS = {
	"xz"    : lzma.LZMACompressor
}

DECOMPRESSORS = {
	"xz"    : lzma.LZMADecompressor,
}

def guess_algo(name=None, fileobj=None):
	"""
		This function takes a filename or a file descriptor
		and tells the name of the algorithm the file was
		compressed with.
		If an unknown or no compression was used, None is returned.
	"""
	ret = None

	if name:
		fileobj = open(file)

	# Save position of pointer.
	pos = fileobj.tell()

	# Iterate over all algoriths and their magic values
	# and check for a match.
	for algo, magic in list(MAGICS.items()):
		fileobj.seek(0)

		start_sequence = fileobj.read(len(magic))
		if start_sequence == magic:
			ret = algo
			break

	# Reset file pointer.
	fileobj.seek(pos)

	if name:
		fileobj.close()

	return ret

def decompressobj(name=None, fileobj=None, algo=ALGO_DEFAULT):
	f_cls = FILES.get(algo, None)
	if not f_cls:
		raise CompressionError(_("Given algorithm '%s' is not supported."))

	f = f_cls(name, fileobj=fileobj, mode="r")

	return f


def compressobj(name=None, fileobj=None, algo=ALGO_DEFAULT):
	f_cls = FILES.get(algo, None)
	if not f_cls:
		raise CompressionError(_("Given algorithm '%s' is not supported."))

	f = f_cls(name, fileobj=fileobj, mode="w")

	return f
