#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2021 Pakfire development team                                 #
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

import logging
import os
import signal
import time

log = logging.getLogger("pakfire.cgroups")

def find_group_by_pid(pid):
	"""
		Returns the cgroup of the process currently running with pid
	"""
	with open("/proc/%s/cgroup" % pid) as f:
		for line in f:
			if not line.startswith("0::"):
				continue

			# Clean up path
			path = line[3:].rstrip()

			return CGroup(path)

def get_own_group():
	"""
		Returns the cgroup of the process we are currently in
	"""
	pid = os.getpid()

	return find_group_by_pid(pid)

class CGroup(object):
	"""
		cgroup controller
	"""
	root = "/sys/fs/cgroup/unified"

	def __init__(self, path):
		if not path.startswith("/"):
			raise ValueError("Invalid cgroup path")

		# Store path
		self.path = path

		# Make absolute path
		self.abspath = "%s%s" % (self.root, self.path)

		if not os.path.isdir(self.abspath):
			raise ValueError("Non-existant cgroup")

	def __repr__(self):
		return "<%s path=%s>" % (self.__class__.__name__, self.path)

	def _open(self, path, mode="r"):
		"""
			Opens a file in this cgroup for reading of writing
		"""
		# Make full path
		path = os.path.join(self.abspath, path)

		return open(path, mode)

	@property
	def parent(self):
		"""
			Returns the parent group
		"""
		return self.__class__(os.path.dirname(self.path))

	def create_subgroup(self, name):
		path = os.path.join(self.path, name)

		# Create directory
		try:
			os.mkdir("%s%s" % (self.root, path))

			log.debug("New cgroup '%s' created" % path)

		# Silently continue if groups already exists
		except FileExistsError:
			pass

		# Return new instance
		return self.__class__(path)

	def destroy(self):
		"""
			Destroys this cgroup
		"""
		log.debug("Destroying cgroup %s" % self.path)

		# Move whatever is left to the parent group
		self.migrate(self.parent)

		# Remove the file tree
		try:
			os.rmdir(self.abspath)
		except OSError as e:
			# Ignore "Device or resource busy".
			if e.errno == 16:
				return

			raise

	@property
	def pids(self):
		"""
			Returns the PIDs of all currently in this group running processes
		"""
		pids = []

		with self._open("cgroup.procs") as f:
			for line in f:
				try:
					pid = int(line)
				except (TypeError, ValueError):
					pass

				pids.append(pid)

		return pids

	def attach_process(self, pid):
		"""
			Attaches the process PID to this group
		"""
		log.debug("Attaching process %s to group %s" % (pid, self.path))

		with self._open("cgroup.procs", "w") as f:
			f.write("%s\n" % pid)

	def attach_self(self):
		"""
			Attaches this process to the group
		"""
		return self.attach_process(os.getpid())

	def detach_self(self):
		pid = os.getpid()

		# Move process to parent
		if pid in self.pids:
			self.parent.attach_process(pid)

	def migrate(self, group):
		"""
			Migrates all processes to the given group
		"""
		for pid in self.pids:
			group.attach_process(pid)

	def _kill(self, signal=signal.SIGTERM):
		"""
			Sends signal to all processes in this cgroup
		"""
		for pid in self.pids:
			log.debug("Sending signal %s to process %s" % (signal, pid))

			try:
				os.kill(pid, signal)
			except OSError as e:
				# Skip "No such process" error
				if e.errno == 3:
					pass
				else:
					raise

		# Return True if there are any processes left
		return not self.pids

	def killall(self, timeout=10):
		"""
			Kills all processes
		"""
		self.detach_self()

		for i in range(timeout * 10):
			if i >= 10:
				s = signal.SIGKILL
			else:
				s = signal.SIGTERM

			# Send signal and end loop when no processes are left
			if self._kill(signal=s):
				break

			# Sleep for 100ms
			time.sleep(0.1)
