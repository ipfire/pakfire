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

import fcntl
import os
import select
import subprocess
import time

from _pakfire import PERSONALITY_LINUX, PERSONALITY_LINUX32

import pakfire.util as util
from errors import *

def logOutput(fds, logger, returnOutput=1, start=0, timeout=0):
	output=""
	done = 0

	# set all fds to nonblocking
	for fd in fds:
		flags = fcntl.fcntl(fd, fcntl.F_GETFL)
		if not fd.closed:
			fcntl.fcntl(fd, fcntl.F_SETFL, flags| os.O_NONBLOCK)

	tail = ""
	while not done:
		if (time.time() - start) > timeout and timeout != 0:
			done = 1
			break

		i_rdy, o_rdy, e_rdy = select.select(fds,[],[],1)

		for s in i_rdy:
			# slurp as much input as is ready
			input = s.read()

			if input == "":
				done = 1
				break

			if logger is not None:
				lines = input.split("\n")
				if tail:
					lines[0] = tail + lines[0]

				# we may not have all of the last line
				tail = lines.pop()

				for line in lines:
					logger.info(line)

				for h in logger.handlers:
					h.flush()

			if returnOutput:
				output += input

	if tail and logger is not None:
		logger.info(tail)

	return output


def do(command, shell=False, chrootPath=None, cwd=None, timeout=0, raiseExc=True, returnOutput=0, personality=None, logger=None, env=None, cgroup=None, *args, **kargs):
	# Save the output of command
	output = ""

	# Save time when command was started
	start = time.time()

	# Create preexecution thingy for command
	preexec = ChildPreExec(personality, chrootPath, cwd)

	if logger:
		logger.debug("Executing command: %s in %s" % (command, chrootPath or "/"))

	child = None

	try:
		# Create new child process
		child = subprocess.Popen(
			command,
			shell=shell,
			bufsize=0, close_fds=True, 
			stdin=open("/dev/null", "r"), 
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			preexec_fn = preexec,
			env=env
		)

		# If cgroup is given, attach the subprocess.
		if cgroup:
			cgroup.attach_task(child.pid)

		# use select() to poll for output so we dont block
		output = logOutput([child.stdout, child.stderr], logger, returnOutput, start, timeout)

	except:
		# kill children if they aren't done
		if child and child.returncode is None:
			os.killpg(child.pid, 9)
		try:
			if child:
				os.waitpid(child.pid, 0)
		except:
			pass
		raise

	# wait until child is done, kill it if it passes timeout
	niceExit=1
	while child.poll() is None:
		if (time.time() - start) > timeout and timeout != 0:
			niceExit = 0
			os.killpg(child.pid, 15)
		if (time.time() - start) > (timeout+1) and timeout != 0:
			niceExit = 0
			os.killpg(child.pid, 9)

	if not niceExit:
		raise commandTimeoutExpired, ("Timeout(%s) expired for command:\n # %s\n%s" % (timeout, command, output))

	if logger:
		logger.debug("Child returncode was: %s" % str(child.returncode))

	if raiseExc and child.returncode:
		if returnOutput:
			raise Error, ("Command failed: \n # %s\n%s" % (command, output), child.returncode)
		else:
			raise Error, ("Command failed. See logs for output.\n # %s" % (command,), child.returncode)

	return output

class ChildPreExec(object):
	def __init__(self, personality, chrootPath, cwd):
		self._personality = personality
		self.chrootPath  = chrootPath
		self.cwd = cwd

	@property
	def personality(self):
		"""
			Return personality value if supported.
			Otherwise return None.
		"""
		personality_defs = {
			"linux64": PERSONALITY_LINUX,
			"linux32": PERSONALITY_LINUX32,
		}

		try:
			return personality_defs[self._personality]
		except KeyError:
			pass

	def __call__(self, *args, **kargs):
		# Set a new process group
		os.setpgrp()

		# Set new personality if we got one.
		if self.personality:
			util.personality(self.personality)

		# Change into new root.
		if self.chrootPath:
			os.chdir(self.chrootPath)
			os.chroot(self.chrootPath)

		# Change to cwd.
		if self.cwd:
			if not os.path.exists(self.cwd):
				os.makedirs(self.cwd)

			os.chdir(self.cwd)
