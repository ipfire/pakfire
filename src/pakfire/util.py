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

from __future__ import division

import fcntl
import hashlib
import math
import os
import progressbar
import random
import shutil
import signal
import string
import struct
import sys
import termios
import time

import logging
log = logging.getLogger("pakfire")

from constants import *
from i18n import _

# Import binary version of version_compare and capability functions
from _pakfire import version_compare, get_capabilities, set_capabilities, personality

def cli_is_interactive():
	"""
		Say weather a shell is interactive or not.
	"""
	if sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty():
		return True

	return False

def ask_user(question):
	"""
		Ask the user the question, he or she can answer with yes or no.

		This function returns True for "yes" and False for "no".

		If the software is running in a non-inteactive shell, no question
		is asked at all and the answer is always "yes".
	"""
	if not cli_is_interactive():
		return True

	print _("%s [y/N]") % question,
	ret = raw_input()
	print # Just an empty line.

	return ret in ("y", "Y", "z", "Z", "j", "J")

def random_string(length=20):
	s = ""

	for i in range(length):
		s += random.choice(string.letters)

	return s

def make_progress(message, maxval, eta=True, speed=False):
	# Return nothing if stdout is not a terminal.
	if not sys.stdout.isatty():
		return

	if not maxval:
		maxval = 1

	pb = progressbar.ProgressBar(maxval)
	pb.add("%-50s" % message)

	bar = progressbar.WidgetBar()
	pb.add(bar)

	if speed:
		percentage = progressbar.WidgetPercentage()
		pb.add(percentage)

		filetransfer = progressbar.WidgetFileTransferSpeed()
		pb.add(filetransfer)

	if eta:
		eta = progressbar.WidgetETA()
		pb.add(eta)

	return pb.start()

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

def ioctl_GWINSZ(fd):
	try:
		return struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
	except:
		pass

def terminal_size():
	cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

	if not cr:
		try:
			fd = os.open(os.ctermid(), os.O_RDONLY)
			cr = ioctl_GWINSZ(fd)
			os.close(fd)
		except:
			pass

	if not cr:
		try:
			cr = (os.environ['LINES'], os.environ['COLUMNS'])
		except:
			cr = (25, 80)

	return int(cr[1]), int(cr[0])

def format_size(s):
	sign = 1

	# If s is negative, we save the sign and run the calculation with the
	# absolute value of s.
	if s < 0:
		sign = -1
		s = -1 * s

	units = (" ", "k", "M", "G", "T")
	unit = 0

	while s >= 1024 and unit < len(units):
		s /= 1024
		unit += 1

	return "%d%s" % (round(s) * sign, units[unit])

def format_time(s):
	return "%02d:%02d" % (s // 60, s % 60)

def format_speed(s):
	return "%sB/s" % format_size(s)

def calc_hash1(filename=None, data=None):
	h = hashlib.new("sha1")

	if filename:
		f = open(filename)
		buf = f.read(BUFFER_SIZE)
		while buf:
			h.update(buf)
			buf = f.read(BUFFER_SIZE)

		f.close()

	elif data:
		h.update(data)

	return h.hexdigest()

def text_wrap(s, length=65):
	if not s:
		return ""

	lines = []

	words = []
	for line in s.splitlines():
		if not line:
			words.append("")
		else:
			words += line.split()

	line = []
	while words:
		word = words.pop(0)

		# An empty words means a line break.
		if not word:
			if line:
				lines.append(" ".join(line))
			lines.append("")
			line = []

		else:
			if len(" ".join(line)) + len(word) >= length:
				lines.append(" ".join(line))
				line = []
				words.insert(0, word)
			else:
				line.append(word)

	if line:
		lines.append(" ".join(line))

	assert not words

	#return "\n".join(lines)
	return lines

def orphans_kill(root, killsig=signal.SIGTERM):
	"""
		kill off anything that is still chrooted.
	"""
	log.debug(_("Killing orphans..."))

	killed = False
	for fn in [d for d in os.listdir("/proc") if d.isdigit()]:
		try:
			r = os.readlink("/proc/%s/root" % fn)
			if os.path.realpath(root) == os.path.realpath(r):
				log.warning(_("Process ID %s is still running in chroot. Killing...") % fn)
				killed = True

				pid = int(fn, 10)
				os.kill(pid, killsig)
				os.waitpid(pid, 0)
		except OSError, e:
			pass

	# If something was killed, wait a couple of seconds to make sure all file descriptors
	# are closed and we can proceed with umounting the filesystems.
	if killed:
		log.warning(_("Waiting for processes to terminate..."))
		time.sleep(3)

		# Calling ourself again to make sure all processes were killed.
		orphans_kill(root, killsig=killsig)

def scriptlet_interpreter(scriptlet):
	"""
		This function returns the interpreter of a scriptlet.
	"""
	# XXX handle ELF?
	interpreter = None

	for line in scriptlet.splitlines():
		if line.startswith("#!/"):
			interpreter = line[2:]
			interpreter = interpreter.split()[0]
		break

	return interpreter
