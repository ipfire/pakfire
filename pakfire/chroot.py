#!/usr/bin/python

import ctypes
import fcntl
import os
import select
import subprocess
import time

from errors import *

_libc = ctypes.cdll.LoadLibrary(None)
_libc.personality.argtypes = [ctypes.c_ulong]
_libc.personality.restype = ctypes.c_int

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
		if (time.time() - start)>timeout and timeout!=0:
			done = 1
			break

		i_rdy,o_rdy,e_rdy = select.select(fds,[],[],1) 
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
					if line == '': continue
					logger.info(line)
				for h in logger.handlers:
					h.flush()
			if returnOutput:
				output += input
	if tail and logger is not None:
		logger.info(tail)
	return output


def do(command, shell=False, chrootPath=None, cwd=None, timeout=0, raiseExc=True, returnOutput=0, personality=None, logger=None, env=None, *args, **kargs):
	# Save the output of command
	output = ""

	# Save time when command was started
	start = time.time()

	# Create preexecution thingy for command
	preexec = ChildPreExec(personality, chrootPath, cwd)

	if logger:
		logger.debug("Executing command: %s in %s" % (command, chrootPath or "/"))

	try:
		child = None

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
		# taken from sys/personality.h
		personality_defs = {
			"linux64": 0x0000,
			"linux32": 0x0008,
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
			res = _libc.personality(self.personality)
			if res == -1:
				raise OSError, "Could not set personality"

		# Change into new root.
		if self.chrootPath:
			os.chdir(self.chrootPath)
			os.chroot(self.chrootPath)

		# Change to cwd.
		if self.cwd:
			os.chdir(self.cwd)
