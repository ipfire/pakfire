#!/usr/bin/python

import os
import shutil
import signal
import time

import logging
log = logging.getLogger("pakfire.cgroups")

CGROUP_MOUNTPOINT = "/sys/fs/cgroup/systemd"

class CGroup(object):
	def __init__(self, name):
		assert supported(), "cgroups are not supported by this kernel"

		self.name = name
		self.path = os.path.join(CGROUP_MOUNTPOINT, name)
		self.path = os.path.abspath(self.path)

		# The parent cgroup.
		self._parent = None

		# Initialize the cgroup.
		self.create()

		log.debug("cgroup '%s' has been successfully initialized." % self.name)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __cmp__(self, other):
		return cmp(self.path, other.path)

	@classmethod
	def find_by_pid(cls, pid):
		"""
			Returns the cgroup of the process with the given PID.

			If no cgroup can be found, None is returned.
		"""
		if not cls.supported:
			return

		for d, subdirs, files in os.walk(CGROUP_MOUNTPOINT):
			if not "tasks" in files:
				continue

			cgroup = cls(d)
			if pid in cgroup.tasks:
				return cgroup

	@staticmethod
	def supported():
		"""
			Returns true, if this hosts supports cgroups.
		"""
		return os.path.ismount(CGROUP_MOUNTPOINT)

	def create(self):
		"""
			Creates the filesystem structure for
			the cgroup.
		"""
		if os.path.exists(self.path):
			return

		log.debug("cgroup '%s' has been created." % self.name)
		os.makedirs(self.path)

	def create_child_cgroup(self, name):
		"""
			Create a child cgroup with name relative to the
			parent cgroup.
		"""
		return self.__class__(os.path.join(self.name, name))

	def attach(self):
		"""
			Attaches this task to the cgroup.
		"""
		pid = os.getpid()
		self.attach_task(pid)

	def destroy(self):
		"""
			Deletes the cgroup.

			All running tasks will be migrated to the parent cgroup.
		"""
		# Don't delete the root cgroup.
		if self == self.root:
			return

		# Move all tasks to the parent.
		self.migrate(self.parent)

		# Just make sure the statement above worked.
		assert self.is_empty(recursive=True), "cgroup must be empty to be destroyed"
		assert not self.processes

		# Remove the file tree.
		try:
			os.rmdir(self.path)
		except OSError, e:
			# Ignore "Device or resource busy".
			if e.errno == 16:
				return

			raise

	def _read(self, file):
		"""
			Reads the contect of file in the cgroup directory.
		"""
		file = os.path.join(self.path, file)

		with open(file) as f:
			return f.read()

	def _read_pids(self, file):
		"""
			Reads file and interprets the lines as a sorted list.
		"""
		_pids = self._read(file)

		pids = []

		for pid in _pids.splitlines():
			try:
				pid = int(pid)
			except ValueError:
				continue

			if pid in pids:
				continue

			pids.append(pid)

		return sorted(pids)

	def _write(self, file, what):
		"""
			Writes what to file in the cgroup directory.
		"""
		file = os.path.join(self.path, file)

		f = open(file, "w")
		f.write("%s" % what)
		f.close()

	@property
	def root(self):
		if self.parent:
			return self.parent.root

		return self

	@property
	def parent(self):
		# Cannot go above CGROUP_MOUNTPOINT.
		if self.path == CGROUP_MOUNTPOINT:
			return

		if self._parent is None:
			parent_name = os.path.dirname(self.name)
			self._parent = CGroup(parent_name)

		return self._parent

	@property
	def subgroups(self):
		subgroups = []

		for name in os.listdir(self.path):
			path = os.path.join(self.path, name)
			if not os.path.isdir(path):
				continue

			name = os.path.join(self.name, name)
			group = CGroup(name)

			subgroups.append(group)

		return subgroups

	def is_empty(self, recursive=False):
		"""
			Returns True if the cgroup is empty.

			Otherwise returns False.
		"""
		if self.tasks:
			return False

		if recursive:
			for subgroup in self.subgroups:
				if subgroup.is_empty(recursive=recursive):
					continue

				return False

		return True

	@property
	def tasks(self):
		"""
			Returns a list of pids of all tasks
			in this process group.
		"""
		return self._read_pids("tasks")

	@property
	def processes(self):
		"""
			Returns a list of pids of all processes
			that are currently running within the cgroup.
		"""
		return self._read_pids("cgroup.procs")

	def attach_task(self, pid):
		"""
			Attaches the task with the given PID to
			the cgroup.
		"""
		self._write("tasks", pid)

	def migrate_task(self, other, pid):
		"""
			Migrates a single task to another cgroup.
		"""
		other.attach_task(pid)

	def migrate(self, other):
		if self.is_empty(recursive=True):
			return

		log.info("Migrating all tasks from '%s' to '%s'." \
			% (self.name, other.name))

		while True:
			# Migrate all tasks to the new cgroup.
			for task in self.tasks:
				self.migrate_task(other, task)

			# Also do that for all subgroups.
			for subgroup in self.subgroups:
				subgroup.migrate(other)

			if self.is_empty():
				break

	def kill(self, sig=signal.SIGTERM, recursive=True):
		killed_processes = []

		mypid = os.getpid()

		while True:
			for proc in self.processes:
				# Don't kill myself.
				if proc == mypid:
					continue

				# Skip all processes that have already been killed.
				if proc in killed_processes:
					continue

				# If we haven't killed the process yet, we kill it.
				log.debug("Sending signal %s to process %s..." % (sig, proc))

				try:
					os.kill(proc, sig)
				except OSError, e:
					# Skip "No such process" error
					if e.errno == 3:
						pass
					else:
						raise

				# Save all killed processes to a list.
				killed_processes.append(proc)

			else:
				# If no processes are left to be killed, we end the loop.
				break

		# Nothing more to do if not in recursive mode.
		if not recursive:
			return

		# Kill all processes in subgroups as well.
		for subgroup in self.subgroups:
			subgroup.kill(sig=sig, recursive=recursive)

	def kill_and_wait(self):
		# Safely kill all processes in the cgroup.
		# This first sends SIGTERM and then checks 8 times
		# after 200ms whether the group is empty. If not,
		# everything what's still in there gets SIGKILL
		# and it is five more times checked if everything
		# went away.

		sig = None
		for i in range(15):
			if i == 0:
				sig = signal.SIGTERM
			elif i == 9:
				sig = signal.SIGKILL
			else:
				sig = None

			# If no signal is given and there are no processes
			# left, our job is done and we can exit.
			if not self.processes:
				break

			if sig:
				# Send sig to all processes in the cgroup.
				log.debug("Sending signal %s to all processes in '%s'." % (sig, self.name))
				self.kill(sig=sig, recursive=True)

			# Sleep for 200ms.
			time.sleep(0.2)

		return self.is_empty()


# Alias for simple access to check if this host supports cgroups.
supported = CGroup.supported

# Alias for simple access to find the cgroup of a certain process.
find_by_pid = CGroup.find_by_pid
