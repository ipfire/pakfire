#!/usr/bin/python3
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

import fcntl
import os
import select
import subprocess
import time

from ._pakfire import PERSONALITY_LINUX, PERSONALITY_LINUX32

from pakfire.i18n import _
import pakfire.util as util
from .errors import *

class ShellExecuteEnvironment(object):
	def __init__(self, command, cwd=None, chroot_path=None, personality=None, shell=False, timeout=0, env=None,
			cgroup=None, logger=None, log_output=True, log_errors=True, record_output=False, record_stdout=True, record_stderr=True):
		# The given command that should be executed.
		self.command = command

		# Change into current working dir.
		self.cwd = cwd

		# Chroot into this directory.
		self.chroot_path = chroot_path

		# The logger where all the output goes.
		self.logger = logger

		# Set timeout.
		self.timeout = timeout

		# Personality.
		self.personality = personality

		# Shell.
		self.shell = shell
		self.env = env

		# cgroup to which the newly created process should be attached.
		self.cgroup = cgroup

		# Timestamp, when execution has been started and ended.
		self.time_start = None
		self.time_end = None

		# Output, that has to be returned.
		self.output = ""
		self.record_output = record_output
		self.record_stdout = record_stdout
		self.record_stderr = record_stderr

		# Log the output and errors?
		self.log_errors = log_errors
		self.log_output = log_output

		# Exit code of command.
		self.exitcode = None

	def execute(self):
		# Save start time.
		self.time_start = time.time()

		if self.logger:
			self.logger.debug(_("Executing command: %s in %s") % (self.command, self.chroot_path or "/"))

		child = None
		try:
			# Create new child process
			child = self.create_subprocess()

			# Record the output.
			self.tee_log(child)
		except:
			# In case there has been an error, kill children if they aren't done
			if child and child.returncode is None:
				os.killpg(child.pid, 9)

			try:
				if child:
					os.waitpid(child.pid, 0)
			except:
				pass

			# Raise original exception.
			raise

		finally:
			# Save end time.
			self.time_end = time.time()

		# wait until child is done, kill it if it passes timeout
		nice_exit = True
		while child.poll() is None:
			if self.timeout_has_been_exceeded():
				nice_exit = False
				os.killpg(child.pid, 15)

			if self.timeout_has_been_exceeded(3):
				nice_exit = False
				os.killpg(child.pid, 9)

		if not nice_exit:
			raise commandTimeoutExpired(_("Command exceeded timeout (%(timeout)d): %(command)s") % (self.timeout, self.command))

		# Save exitcode.
		self.exitcode = child.returncode

		if self.logger:
			self.logger.debug(_("Child returncode was: %s") % self.exitcode)

		if self.exitcode and self.log_errors:
			raise ShellEnvironmentError(_("Command failed: %s") % self.command, self.exitcode)

		return self.exitcode

	def create_subprocess(self):
		# Create preexecution thingy for command
		preexec_fn = ChildPreExec(self.personality, self.chroot_path, self.cwd)

		kwargs = {
			"bufsize"    : 0,
			"close_fds"  : True,
			"env"        : self.env,
			"preexec_fn" : preexec_fn,
			"shell"      : self.shell,
		}

		# File descriptors.
		stdin = open("/dev/null", "r")

		if self.record_stdout:
			stdout = subprocess.PIPE
		else:
			stdout = open("/dev/null", "w")

		if self.record_stderr:
			stderr = subprocess.PIPE
		else:
			stderr = open("/dev/null", "w")

		kwargs.update({
			"stdin"  : stdin,
			"stdout" : stdout,
			"stderr" : stderr,
		})

		child = subprocess.Popen(self.command, **kwargs)

		# If cgroup is given, attach the subprocess.
		if self.cgroup:
			self.cgroup.attach_task(child.pid)

		return child

	def timeout_has_been_exceeded(self, offset=0):
		"""
			Returns true when the command has been running
			for more than 'timeout' seconds.
		"""
		# If no timeout has been configured, it can never be exceeded.
		if not self.timeout:
			return False

		# Check if the command has already been started.
		if not self.time_start:
			return False

		return (time.time() - self.time_start - offset) > self.timeout

	def tee_log(self, child):
		fds = []

		if self.record_stdout:
			fds.append(child.stdout)

		if self.record_stderr:
			fds.append(child.stderr)

		# Set all file descriptors as non-blocking.
		for fd in fds:
			# Skip already closed file descriptors.
			if fd.closed:
				continue

			flags = fcntl.fcntl(fd, fcntl.F_GETFL)
			fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

		done = False
		tail = ""
		while not done:
			# Check if timeout has been hit.
			if self.timeout_has_been_exceeded():
				done = True
				break

			# Start the select() call.
			i_rdy, o_rdy, e_rdy = select.select(fds, [], [], 1)

			# Process output.
			for s in i_rdy:
				# Read as much data as possible.
				input = s.read()

				if input == "":
					done = True
					break

				if self.record_output:
					self.output += input

				if self.log_output and self.logger:
					lines = input.split("\n")
					if tail:
						lines[0] = tail + lines[0]

					# We may not have got all the characters of the last line.
					tail = lines.pop()

					for line in lines:
						self.logger.info(line)

					# Flush all handlers of the logger.
					for h in self.logger.handlers:
						h.flush()

		# Log the rest of the last line.
		if tail and self.log_output and self.logger:
			self.logger.info(tail)


class ChildPreExec(object):
	def __init__(self, personality, chroot_path, cwd):
		self._personality = personality
		self.chroot_path  = chroot_path
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
		if self.chroot_path:
			os.chdir(self.chroot_path)
			os.chroot(self.chroot_path)

		# Change to cwd.
		if self.cwd:
			if not os.path.exists(self.cwd):
				os.makedirs(self.cwd)

			os.chdir(self.cwd)
