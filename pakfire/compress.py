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

import lzma
import os
import progressbar
import zlib

from constants import *
from i18n import _

PROGRESS_WIDGETS = [
	progressbar.Bar(left="[", right="]"),
	"  ",
	progressbar.Percentage(),
	"  ",
	progressbar.ETA(),
	"  ",
]

def __compress_helper(i, o, comp, flush, progress=None):
	if progress:
		widgets = [ "%-30s  " % os.path.basename(filename)] + PROGRESS_WIDGETS

		maxval = os.path.getsize(filename)

		progress = progressbar.ProgressBar(
			widgets=widgets,
			maxval=maxval,
		)

		progress.start()

	size = 0
	buf = i.read(BUFFER_SIZE)
	while buf:
		if progress:
			size += len(buf)
			progress.update(size)

		o.write(comp(buf))

		buf = i.read(BUFFER_SIZE)

	o.write(flush())

	if progress:
		progress.finish()

def compress(filename, filename2=None, algo="xz", progress=None):
	i = open(filename)

	if not filename2:
		filename2 = filename
		os.unlink(filename)

	o = open(filename2, "w")

	compressobj(i, o, algo="xz", progress=None)

	i.close()
	o.close()

def compressobj(i, o, algo="xz", progress=None):
	comp = None
	if algo == "xz":
		comp = lzma.LZMACompressor()

	elif algo == "zlib":
		comp = zlib.compressobj(9)

	return __compress_helper(i, o, comp.compress, comp.flush, progress=progress)

def decompress(filename, filename2=None, algo="xz", progress=None):
	i = open(filename)

	if not filename2:
		filename2 = filename
		os.unlink(filename)

	o = open(filename2, "w")

	decompressobj(i, o, algo="xz", progress=None)

	i.close()
	o.close()

def decompressobj(i, o, algo="xz", progress=None):
	comp = None
	if algo == "xz":
		comp = lzma.LZMADecompressor()

	elif algo == "zlib":
		comp = zlib.decompressobj(9)

	return __compress_helper(i, o, comp.decompress, comp.flush, progress=progress)

def compress_file(inputfile, outputfile, message="", algo="xz", progress=True):
	"""
		Compress a file in place.
	"""
	assert os.path.exists(inputfile)

	# Get total size of the file for the progressbar.
	total_size = os.path.getsize(inputfile)

	# Open the input file for reading.
	i = open(inputfile, "r")

	# Open the output file for wrinting.
	o = open(outputfile, "w")

	if progress:
		if not message:
			message = _("Compressing %s") % os.path.basename(filename)

		progress = progressbar.ProgressBar(
			widgets = ["%-40s" % message, " ",] + PROGRESS_WIDGETS,
			maxval = total_size,
		)

		progress.start()

	if algo == "xz":
		compressor = lzma.LZMACompressor()
	elif algo == "zlib":
		comp = zlib.decompressobj(9)
	else:
		raise Exception, "Unknown compression choosen: %s" % algo

	size = 0
	while True:
		buf = i.read(BUFFER_SIZE)
		if not buf:
			break

		# Update progressbar.
		size += len(buf)
		if progress:
			progress.update(size)

		# Compress the bits in buf.
		buf = compressor.compress(buf)

		# Write the compressed output.
		o.write(buf)

	# Flush all buffers.
	buf = compressor.flush()
	o.write(buf)

	# Close the progress bar.
	if progress:
		progress.finish()

	i.close()
	o.close()
