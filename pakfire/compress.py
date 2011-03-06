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


def __compress_helper(filename, comp, flush, progress=None):
	if progress:
		widgets = [ "%-30s  " % os.path.basename(filename)] + PROGRESS_WIDGETS

		maxval = os.path.getsize(filename)
		
		progress = progressbar.ProgressBar(
			widgets=widgets,
			maxval=maxval,
			term_width=80,
		)

		progress.start()

	i = open(filename)
	os.unlink(filename)

	o = open(filename, "w")

	size = 0
	buf = i.read(BUFFER_SIZE)
	while buf:
		if progress:
			size += len(buf)
			progress.update(size)

		o.write(comp(buf))

		buf = i.read(BUFFER_SIZE)

	o.write(flush())

	i.close()
	o.close()

	if progress:
		progress.finish()


def compress(filename, algo="xz", progress=None):
	comp = None
	if algo == "xz":
		comp = lzma.LZMACompressor()

	elif algo == "zlib":
		comp = zlib.compressobj(9)

	return __compress_helper(filename, comp.compress, comp.flush,
		progress=progress)


def decompress(filename, algo="xz", progress=None):
	comp = None
	if algo == "xz":
		comp = lzma.LZMADecompressor()

	elif algo == "zlib":
		comp = zlib.decompressobj(9)

	return __compress_helper(filename, comp.decompress, comp.flush,
		progress=progress)


if __name__ == "__main__":
	decompress("test.img", progress=True)
