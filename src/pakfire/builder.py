#!/usr/bin/python3
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
import grp
import math
import os
import re
import shutil
import socket
import tempfile
import time
import uuid

from . import _pakfire
from . import base
from . import cgroup as cgroups
from . import config
from . import downloaders
from . import logger
from . import packages
from . import repository
from . import shell
from . import util

import logging
log = logging.getLogger("pakfire.builder")

from .system import system
from .constants import *
from .i18n import _
from .errors import BuildError, BuildRootLocked, Error


BUILD_LOG_HEADER = """
 ____       _     __ _            _           _ _     _
|  _ \ __ _| | __/ _(_)_ __ ___  | |__  _   _(_) | __| | ___ _ __
| |_) / _` | |/ / |_| | '__/ _ \ | '_ \| | | | | |/ _` |/ _ \ '__|
|  __/ (_| |   <|  _| | | |  __/ | |_) | |_| | | | (_| |  __/ |
|_|   \__,_|_|\_\_| |_|_|  \___| |_.__/ \__,_|_|_|\__,_|\___|_|

	Version : %(version)s
	Host    : %(hostname)s (%(host_arch)s)
	Time    : %(time)s

"""

class Builder(object):
	def __init__(self, arch=None, build_id=None, logfile=None, **kwargs):
		self.config = config.Config("general.conf", "builder.conf")

		distro_name = self.config.get("builder", "distro", None)
		if distro_name:
			self.config.read("distros/%s.conf" % distro_name)

		# Settings array.
		self.settings = {
			"enable_loop_devices" : self.config.get_bool("builder", "use_loop_devices", True),
			"enable_ccache"       : self.config.get_bool("builder", "use_ccache", True),
			"buildroot_tmpfs"     : self.config.get_bool("builder", "use_tmpfs", False),
			"private_network"     : self.config.get_bool("builder", "private_network", False),
		}

		# Get ccache settings.
		if self.settings.get("enable_ccache", False):
			self.settings.update({
				"ccache_compress" : self.config.get_bool("ccache", "compress", True),
			})

		# Add settings from keyword arguments
		self.settings.update(kwargs)

		# Setup logging
		self.setup_logging(logfile)

		# Generate a build ID
		self.build_id = build_id or "%s" % uuid.uuid4()

		# Path
		self.path = os.path.join(BUILD_ROOT, self.build_id)
		self._lock = None

		# Architecture to build for
		self.arch = arch or _pakfire.native_arch()

		# Check if this host can build the requested architecture.
		if not _pakfire.arch_supported_by_host(self.arch):
			raise BuildError(_("Cannot build for %s on this host") % self.arch)

		# Initialize cgroups
		self.cgroup = self._make_cgroup()

		# Unshare namepsace.
		# If this fails because the kernel has no support for CLONE_NEWIPC or CLONE_NEWUTS,
		# we try to fall back to just set CLONE_NEWNS.
		try:
			_pakfire.unshare(_pakfire.SCHED_CLONE_NEWNS|_pakfire.SCHED_CLONE_NEWIPC|_pakfire.SCHED_CLONE_NEWUTS)
		except RuntimeError as e:
			_pakfire.unshare(_pakfire.SCHED_CLONE_NEWNS)

		# Optionally enable private networking.
		if self.settings.get("private_network", None):
			_pakfire.unshare(_pakfire.SCHED_CLONE_NEWNET)

	def __enter__(self):
		self.log.debug("Entering %s" % self.path)

		# Mount the directories
		try:
			self._mountall()
		except OSError as e:
			if e.errno == 30: # Read-only FS
				raise BuildError("Buildroot is read-only: %s" % self.path)

			# Raise all other errors
			raise

		# Lock the build environment
		self.lock()

		# Populate /dev
		self.populate_dev()

		# Setup domain name resolution in chroot
		self.setup_dns()

		return BuilderContext(self)

	def __exit__(self, type, value, traceback):
		self.log.debug("Leaving %s" % self.path)

		# Kill all remaining processes in the build environment
		self.cgroup.killall()

		# Destroy the cgroup
		self.cgroup.destroy()
		self.cgroup = None

		# Umount the build environment
		self._umountall()

		# Unlock build environment
		self.unlock()

		# Delete everything
		self._destroy()

	def setup_logging(self, logfile):
		if logfile:
			self.log = log.getChild(self.build_id)
			# Propage everything to the root logger that we will see something
			# on the terminal.
			self.log.propagate = 1
			self.log.setLevel(logging.INFO)

			# Add the given logfile to the logger.
			h = logging.FileHandler(logfile)
			self.log.addHandler(h)

			# Format the log output for the file.
			f = logger.BuildFormatter()
			h.setFormatter(f)
		else:
			# If no logile was given, we use the root logger.
			self.log = logging.getLogger("pakfire")

	def _make_cgroup(self):
		"""
			Initialises a cgroup so that we can enforce resource limits
			and can identify processes belonging to this build environment.
		"""
		# Find our current group
		parent = cgroups.get_own_group()

		# Create a sub-group
		cgroup = parent.create_subgroup("pakfire-%s" % self.build_id)

		# Make this process join the new group
		cgroup.attach_self()

		return cgroup

	def lock(self):
		filename = os.path.join(self.path, ".lock")

		try:
			self._lock = open(filename, "a+")
		except IOError as e:
			return 0

		try:
			fcntl.lockf(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
		except IOError as e:
			raise BuildRootLocked("Buildroot is locked")

		return 1

	def unlock(self):
		if self._lock:
			self._lock.close()
			self._lock = None

	def _destroy(self):
		self.log.debug("Destroying environment %s" % self.path)

		if os.path.exists(self.path):
			util.rm(self.path)

	@property
	def mountpoints(self):
		mountpoints = []

		# Make root as a tmpfs if enabled.
		if self.settings.get("buildroot_tmpfs"):
			mountpoints += [
				("pakfire_root", "/", "tmpfs", "defaults"),
			]

		mountpoints += [
			# src, dest, fs, options
			("pakfire_proc",  "/proc",     "proc",  "nosuid,noexec,nodev"),
			("/proc/sys",     "/proc/sys", "bind",  "bind"),
			("/proc/sys",     "/proc/sys", "bind",  "bind,ro,remount"),
			("/sys",          "/sys",      "bind",  "bind"),
			("/sys",          "/sys",      "bind",  "bind,ro,remount"),
			("pakfire_tmpfs", "/dev",      "tmpfs", "mode=755,nosuid"),
			("/dev/pts",      "/dev/pts",  "bind",  "bind"),
			("pakfire_tmpfs", "/run",      "tmpfs", "mode=755,nosuid,nodev"),
			("pakfire_tmpfs", "/tmp",      "tmpfs", "mode=755,nosuid,nodev"),
		]

		# If selinux is enabled.
		if os.path.exists("/sys/fs/selinux"):
			mountpoints += [
				("/sys/fs/selinux", "/sys/fs/selinux", "bind", "bind"),
				("/sys/fs/selinux", "/sys/fs/selinux", "bind", "bind,ro,remount"),
			]

		# If ccache support is requested, we bind mount the cache.
		if self.settings.get("enable_ccache"):
			# Create ccache cache directory if it does not exist.
			if not os.path.exists(CCACHE_CACHE_DIR):
				os.makedirs(CCACHE_CACHE_DIR)

			mountpoints += [
				(CCACHE_CACHE_DIR, "/var/cache/ccache", "bind", "bind"),
			]

		return mountpoints

	def _mountall(self):
		self.log.debug("Mounting environment")

		for src, dest, fs, options in self.mountpoints:
			mountpoint = self.chrootPath(dest)
			if options:
				options = "-o %s" % options

			# Eventually create mountpoint directory
			if not os.path.exists(mountpoint):
				os.makedirs(mountpoint)

			self.execute_root("mount -n -t %s %s %s %s" % (fs, options, src, mountpoint), shell=True)

	def _umountall(self):
		self.log.debug("Umounting environment")

		mountpoints = []
		for src, dest, fs, options in reversed(self.mountpoints):
			dest = self.chrootPath(dest)

			if not dest in mountpoints:
				mountpoints.append(dest)

		while mountpoints:
			for mp in mountpoints:
				try:
					self.execute_root("umount -n %s" % mp, shell=True)
				except ShellEnvironmentError:
					pass

				if not os.path.ismount(mp):
					mountpoints.remove(mp)

	def copyin(self, file_out, file_in):
		if file_in.startswith("/"):
			file_in = file_in[1:]

		file_in = self.chrootPath(file_in)

		#if not os.path.exists(file_out):
		#	return

		dir_in = os.path.dirname(file_in)
		if not os.path.exists(dir_in):
			os.makedirs(dir_in)

		self.log.debug("%s --> %s" % (file_out, file_in))

		shutil.copy2(file_out, file_in)

	def copyout(self, file_in, file_out):
		if file_in.startswith("/"):
			file_in = file_in[1:]

		file_in = self.chrootPath(file_in)

		#if not os.path.exists(file_in):
		#	return

		dir_out = os.path.dirname(file_out)
		if not os.path.exists(dir_out):
			os.makedirs(dir_out)

		self.log.debug("%s --> %s" % (file_in, file_out))

		shutil.copy2(file_in, file_out)

	def populate_dev(self):
		nodes = [
			"/dev/null",
			"/dev/zero",
			"/dev/full",
			"/dev/random",
			"/dev/urandom",
			"/dev/tty",
			"/dev/ptmx",
			"/dev/kmsg",
			"/dev/rtc0",
			"/dev/console",
		]

		# If we need loop devices (which are optional) we create them here.
		if self.settings["enable_loop_devices"]:
			for i in range(0, 7):
				nodes.append("/dev/loop%d" % i)

		for node in nodes:
			# Stat the original node of the host system and copy it to
			# the build chroot.
			try:
				node_stat = os.stat(node)

			# If it cannot be found, just go on.
			except OSError:
				continue

			self._create_node(node, node_stat.st_mode, node_stat.st_rdev)

		os.symlink("/proc/self/fd/0", self.chrootPath("dev", "stdin"))
		os.symlink("/proc/self/fd/1", self.chrootPath("dev", "stdout"))
		os.symlink("/proc/self/fd/2", self.chrootPath("dev", "stderr"))
		os.symlink("/proc/self/fd",   self.chrootPath("dev", "fd"))

	def chrootPath(self, *args):
		# Remove all leading slashes
		_args = []
		for arg in args:
			if arg.startswith("/"):
				arg = arg[1:]
			_args.append(arg)
		args = _args

		ret = os.path.join(self.path, *args)
		ret = ret.replace("//", "/")

		assert ret.startswith(self.path)

		return ret

	def setup_dns(self):
		"""
			Add DNS resolution facility to chroot environment by copying
			/etc/resolv.conf and /etc/hosts.
		"""
		for i in ("/etc/resolv.conf", "/etc/hosts"):
			self.copyin(i, i)

	def _create_node(self, filename, mode, device):
		self.log.debug("Create node: %s (%s)" % (filename, mode))

		filename = self.chrootPath(filename)

		# Create parent directory if it is missing.
		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		os.mknod(filename, mode, device)

	def execute_root(self, command, **kwargs):
		"""
			Executes the given command outside the build chroot.
		"""
		shellenv = shell.ShellExecuteEnvironment(command, logger=self.log, **kwargs)
		shellenv.execute()

		return shellenv


class BuilderContext(object):
	def __init__(self, builder):
		self.builder = builder

		# Get a reference to the logger
		self.log = self.builder.log

		# Initialise Pakfire instance
		self.pakfire = base.Pakfire(
			path=self.builder.path,
			config=self.builder.config,
			distro=self.builder.config.distro,
			arch=self.builder.arch,
		)

		self.setup()

	@property
	def environ(self):
		env = MINIMAL_ENVIRONMENT.copy()
		env.update({
			# Add HOME manually, because it is occasionally not set
			# and some builds get in trouble then.
			"TERM" : os.environ.get("TERM", "vt100"),

			# Sanitize language.
			"LANG" : os.environ.setdefault("LANG", "en_US.UTF-8"),
		})

		# Inherit environment from distro
		env.update(self.pakfire.distro.environ)

		# ccache environment settings
		if self.builder.settings.get("enable_ccache", False):
			compress = self.builder.settings.get("ccache_compress", False)
			if compress:
				env["CCACHE_COMPRESS"] = "1"

			# Let ccache create its temporary files in /tmp.
			env["CCACHE_TEMPDIR"] = "/tmp"

		# Fake UTS_MACHINE, when we cannot use the personality syscall and
		# if the host architecture is not equal to the target architecture.
		if not _pakfire.native_arch() == self.pakfire.arch:
			env.update({
				"LD_PRELOAD"  : "/usr/lib/libpakfire_preload.so",
				"UTS_MACHINE" : self.pakfire.arch,
			})

		return env

	def setup(self, install=None):
		self.log.info(_("Install packages needed for build..."))

		packages = [
			"@Build",
		]

		# If we have ccache enabled, we need to extract it
		# to the build chroot
		if self.builder.settings.get("enable_ccache"):
			packages.append("ccache")

		# Install additional packages
		if install:
			packages += install

		# Logging
		self.log.debug(_("Installing build requirements: %s") % ", ".join(packages))

		# Initialise Pakfire
		with self.pakfire as p:
			# Install all required packages
			transaction = p.install(packages)

			# Dump transaction to log
			t = transaction.dump()
			self.log.info(t)

			# Download transaction
			d = downloaders.TransactionDownloader(self.pakfire, transaction)
			d.download()

			# Run the transaction
			transaction.run()

	def build(self, package, private_network=True, shell=True):
		archive = _pakfire.Archive(self.pakfire, package)

		requires = archive.get("dependencies.requires")

		# Setup the environment including any build dependencies
		self.setup(install=requires.splitlines())

	def shell(self, install=[]):
		if not util.cli_is_interactive():
			self.log.warning("Cannot run shell on non-interactive console.")
			return

		# Install our standard shell packages
		install += SHELL_PACKAGES

		self.setup(install=install)

		command = "/usr/sbin/chroot %s %s %s" % (self.chrootPath(), SHELL_SCRIPT)

		# Add personality if we require one
		if self.pakfire.distro.personality:
			command = "%s %s" % (self.pakfire.distro.personality, command)

		for key, val in list(self.environ.items()):
			command = "%s=\"%s\" " % (key, val) + command

		# Empty the environment
		command = "env -i - %s" % command

		self.log.debug("Shell command: %s" % command)

		shell = os.system(command)
		return os.WEXITSTATUS(shell)
