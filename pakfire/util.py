#!/usr/bin/python

import os
import progressbar
import random
import shutil
import string
import sys
import time

from errors import Error
from packages.util import calc_hash1, format_size

def cli_is_interactive():
	"""
		Say weather a shell is interactive or not.
	"""
	if sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty():
		return True

	return False

def random_string(length=20):
	s = ""

	for i in range(length):
		s += random.choice(string.letters)

	return s

def make_progress(message, maxval):
	# Return nothing if stdout is not a terminal.
	if not sys.stdout.isatty():
		return

	widgets = [
		"  ",
		"%-40s" % message,
		" ",
		progressbar.Bar(left="[", right="]"),
		"  ",
		progressbar.ETA(),
		"  ",
	]

	if not maxval:
		maxval = 1

	pb = progressbar.ProgressBar(widgets=widgets, maxval=maxval)
	pb.start()

	return pb

def rm(path, *args, **kargs):
	"""
		version of shutil.rmtree that ignores no-such-file-or-directory errors,
		and tries harder if it finds immutable files
	"""
	tryAgain = 1
	failedFilename = None
	while tryAgain:
		tryAgain = 0
		try:
			shutil.rmtree(path, *args, **kargs)
		except OSError, e:
			if e.errno == 2: # no such file or directory
				pass
			elif e.errno==1 or e.errno==13:
				tryAgain = 1
				if failedFilename == e.filename:
					raise
				failedFilename = e.filename
				os.system("chattr -R -i %s" % path)
			else:
				raise
