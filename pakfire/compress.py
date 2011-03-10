#!/usr/bin/python

import lzma
import os
import progressbar
import zlib

from constants import *

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

