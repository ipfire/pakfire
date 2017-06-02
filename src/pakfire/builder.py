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
from . import cgroup
from . import config
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
	def __init__(self, package=None, arch=None, build_id=None, logfile=None, **kwargs):
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
		self.arch = arch or system.arch

		# Check if this host can build the requested architecture.
		if not system.host_supports_arch(self.arch):
			raise BuildError(_("Cannot build for %s on this host") % self.arch)

		# Initialize a cgroup (if supported)
		self.cgroup = self.make_cgroup()

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

		# Create Pakfire instance
		self.pakfire = base.Pakfire(path=self.path, config=self.config, distro=self.config.distro, arch=arch)

	def __del__(self):
		"""
			Releases build environment and clean up
		"""
		# Umount the build environment
		self._umountall()

		# Destroy the pakfire instance
		del self.pakfire

		# Unlock build environment
		self.unlock()

		# Delete everything
		self._destroy()

	def __enter__(self):
		self.log.debug("Entering %s" % self.path)

		# Mount the directories
		try:
			self._mountall()
		except OSError as e:
			if e.errno == 30: # Read-only FS
				raise BuildError("Buildroot is read-only: %s" % self.pakfire.path)

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
		if self.cgroup:
			# Move the builder process out of the cgroup.
			self.cgroup.migrate_task(self.cgroup.parent, os.getpid())

			# Kill all still running processes in the cgroup.
			self.cgroup.kill_and_wait()

			# Remove cgroup and all parent cgroups if they are empty.
			self.cgroup.destroy()

			parent = self.cgroup.parent
			while parent:
				if not parent.is_empty(recursive=True):
					break

				parent.destroy()
				parent = parent.parent

		else:
			util.orphans_kill(self.path)

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

	def make_cgroup(self):
		"""
			Initialize cgroup (if the system supports it).
		"""
		if not cgroup.supported():
			return

		# Search for the cgroup this process is currently running in.
		parent_cgroup = cgroup.find_by_pid(os.getpid())
		if not parent_cgroup:
			return

		# Create our own cgroup inside the parent cgroup.
		c = parent_cgroup.create_child_cgroup("pakfire/builder/%s" % self.build_id)

		# Attach the pakfire-builder process to the group.
		c.attach()

		return c

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

		# Get a reference to Pakfire
		self.pakfire = self.builder.pakfire

		# Get a reference to the logger
		self.log = self.builder.log

	@property
	def environ(self):
		env = MINIMAL_ENVIRONMENT.copy()
		env.update({
			# Add HOME manually, because it is occasionally not set
			# and some builds get in trouble then.
			"TERM" : os.environ.get("TERM", "vt100"),

			# Sanitize language.
			"LANG" : os.environ.setdefault("LANG", "en_US.UTF-8"),

			# Set the container that we can detect, if we are inside a
			# chroot.
			"container" : "pakfire-builder",
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
		if not self.pakfire.arch.personality and \
				not system.native_arch == self.pakfire.arch.name:
			env.update({
				"LD_PRELOAD"  : "/usr/lib/libpakfire_preload.so",
				"UTS_MACHINE" : self.pakfire.arch.name,
			})

		return env

	def setup(self, install=None):
		self.log.info(_("Install packages needed for build..."))

		packages = [
			"@Build",
			"pakfire-build >= %s" % self.pakfire.__version__,
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

		# Initialise Pakfire and install all required packages
		with self.pakfire as p:
			p.install(packages)

	def build(self, package, private_network=True, shell=True):
		package = self._prepare_package(package)
		assert package

		# Setup the environment including any build dependencies
		self.setup(install=package.requires)

	def _prepare_package(self, package):
		# Check if the file exists
		if not os.path.exists(package):
			raise FileNotFoundError(package)

		# Try opening the package
		return packages.open(self.pakfire, None, package)

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


class BuildEnviron(object):
	def __init__(self, pakfire, filename=None, distro_name=None, build_id=None, logfile=None, release_build=True, **kwargs):
		self.pakfire = pakfire

		# This build is a release build?
		self.release_build = release_build

		if self.release_build:
			# Disable the local build repository in release mode.
			self.pakfire.repos.disable_repo("build")

			# Log information about pakfire and some more information, when we
			# are running in release mode.
			logdata = {
				"host_arch"  : system.arch,
				"hostname"   : system.hostname,
				"time"       : time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()),
				"version"    : "Pakfire %s" % PAKFIRE_VERSION,
			}

			for line in BUILD_LOG_HEADER.splitlines():
				self.log.info(line % logdata)

		# Where do we put the result?
		self.resultdir = os.path.join(self.pakfire.path, "result")

		# Open package.
		# If we have a plain makefile, we first build a source package and go with that.
		if filename:
			# Open source package.
			self.pkg = packages.SourcePackage(self.pakfire, None, filename)
			assert self.pkg, filename

			# Log the package information.
			self.log.info(_("Package information:"))
			for line in self.pkg.dump(int=True).splitlines():
				self.log.info("  %s" % line)
			self.log.info("")

			# Path where we extract the package and put all the source files.
			self.build_dir = os.path.join(self.path, "usr/src/packages", self.pkg.friendly_name)
		else:
			# No package :(
			self.pkg = None

		# Lock the buildroot
		self._lock = None

		# Save the build time.
		self.build_time = time.time()

	def start(self):
		# Extract all needed packages.
		self.extract()

	def stop(self):
		# Shut down pakfire instance.
		self.pakfire.destroy()

	@property
	def config(self):
		"""
			Proxy method for easy access to the configuration.
		"""
		return self.pakfire.config

	@property
	def distro(self):
		"""
			Proxy method for easy access to the distribution.
		"""
		return self.pakfire.distro

	@property
	def path(self):
		"""
			Proxy method for easy access to the path.
		"""
		return self.pakfire.path

	@property
	def arch(self):
		"""
			Inherit architecture from distribution configuration.
		"""
		return self.pakfire.distro.arch

	@property
	def personality(self):
		"""
			Gets the personality from the distribution configuration.
		"""
		return self.pakfire.distro.personality

	@property
	def info(self):
		return {
			"build_date" : time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(self.build_time)),
			"build_host" : socket.gethostname(),
			"build_id"   : self.build_id,
			"build_time" : self.build_time,
		}

	@property
	def keyring(self):
		"""
			Shortcut to access the pakfire keyring.
		"""
		return self.pakfire.keyring

	def copy_result(self, resultdir):
		# XXX should use find_result_packages

		dir_in = self.chrootPath("result")

		for dir, subdirs, files in os.walk(dir_in):
			basename = os.path.basename(dir)
			dir = dir[len(self.chrootPath()):]
			for file in files:
				file_in = os.path.join(dir, file)

				file_out = os.path.join(
					resultdir,
					basename,
					file,
				)

				self.copyout(file_in, file_out)

	def find_result_packages(self):
		ret = []

		for dir, subdirs, files in os.walk(self.resultdir):
			for file in files:
				if not file.endswith(".%s" % PACKAGE_EXTENSION):
					continue

				file = os.path.join(dir, file)
				ret.append(file)

		return ret

	def extract(self, requires=None):
		"""
			Gets a dependency set and extracts all packages
			to the environment.
		"""
		if not requires:
			requires = []

		# Add neccessary build dependencies.
		requires += BUILD_PACKAGES

		# If we have ccache enabled, we need to extract it
		# to the build chroot.
		if self.settings.get("enable_ccache"):
			requires.append("ccache")

		# Get build dependencies from source package.
		if self.pkg:
			for req in self.pkg.requires:
				requires.append(req)

		# Install all packages.
		self.log.info(_("Install packages needed for build..."))
		self.install(requires)

		# Copy the makefile and load source tarballs.
		if self.pkg:
			self.pkg.extract(_("Extracting"), prefix=self.build_dir)

			# Add an empty line at the end.
			self.log.info("")

	def install(self, requires, **kwargs):
		"""
			Install everything that is required in requires.
		"""
		# If we got nothing to do, we quit immediately.
		if not requires:
			return

		kwargs.update({
			"interactive" : False,
			"logger" : self.log,
		})

		if "allow_downgrade" not in kwargs:
			kwargs["allow_downgrade"] = True

		# Install everything.
		self.pakfire.install(requires, **kwargs)

	def cleanup(self):
		self.log.debug("Cleaning environemnt.")

		# Remove the build directory and buildroot.
		dirs = (self.build_dir, self.chrootPath("result"),)

		for d in dirs:
			if not os.path.exists(d):
				continue

			util.rm(d)
			os.makedirs(d)

	@property
	def installed_packages(self):
		"""
			Returns an iterator over all installed packages in this build environment.
		"""
		# Get the repository of all installed packages.
		repo = self.pakfire.repos.get_repo("@system")

		# Return an iterator over the packages.
		return iter(repo)

	def write_config(self):
		# Cleanup everything in /etc/pakfire.
		util.rm(self.chrootPath(CONFIG_DIR))

		for i in (CONFIG_DIR, CONFIG_REPOS_DIR):
			i = self.chrootPath(i)
			if not os.path.exists(i):
				os.makedirs(i)

		# Write general.conf.
		f = open(self.chrootPath(CONFIG_DIR, "general.conf"), "w")
		f.close()

		# Write builder.conf.
		f = open(self.chrootPath(CONFIG_DIR, "builder.conf"), "w")
		f.write(self.distro.get_config())
		f.close()

		# Create pakfire configuration files.
		for repo in self.pakfire.repos:
			conf = repo.get_config()

			if not conf:
				continue

			filename = self.chrootPath(CONFIG_REPOS_DIR, "%s.repo" % repo.name)
			f = open(filename, "w")
			f.write("\n".join(conf))
			f.close()

	@property
	def pkg_makefile(self):
		return os.path.join(self.build_dir, "%s.%s" % (self.pkg.name, MAKEFILE_EXTENSION))

	def execute(self, command, logger=None, **kwargs):
		"""
			Executes the given command in the build chroot.
		"""
		# Environment variables
		env = self.environ

		if "env" in kwargs:
			env.update(kwargs.pop("env"))

		self.log.debug("Environment:")
		for k, v in sorted(env.items()):
			self.log.debug("  %s=%s" % (k, v))

		# Make every shell to a login shell because we set a lot of
		# environment things there.
		command = ["bash", "--login", "-c", command]

		args = {
			"chroot_path" : self.chrootPath(),
			"cgroup"      : self.cgroup,
			"env"         : env,
			"logger"      : logger,
			"personality" : self.personality,
			"shell"       : False,
		}
		args.update(kwargs)

		# Run the shit.
		shellenv = shell.ShellExecuteEnvironment(command, **args)
		shellenv.execute()

		return shellenv

	def build(self, install_test=True, prepare=False):
		if not self.pkg:
			raise BuildError(_("You cannot run a build when no package was given."))

		# Search for the package file in build_dir and raise BuildError if it is not present.
		if not os.path.exists(self.pkg_makefile):
			raise BuildError(_("Could not find makefile in build root: %s") % self.pkg_makefile)

		# Write pakfire configuration into the chroot.
		self.write_config()

		# Create the build command, that is executed in the chroot.
		build_command = [
			"/usr/lib/pakfire/builder",
			"--offline",
			"build",
			"/%s" % os.path.relpath(self.pkg_makefile, self.chrootPath()),
			"--arch", self.arch,
			"--nodeps",
			"--resultdir=/result",
		]

		# Check if only the preparation stage should be run.
		if prepare:
			build_command.append("--prepare")

		build_command = " ".join(build_command)

		try:
			self.execute(build_command, logger=self.log)

			# Perform the install test after the actual build.
			if install_test and not prepare:
				self.install_test()

		except ShellEnvironmentError:
			self.log.error(_("Build failed"))

		except KeyboardInterrupt:
			self.log.error(_("Build interrupted"))

			raise

		# Catch all other errors.
		except:
			self.log.error(_("Build failed."), exc_info=True)

		else:
			# Don't sign packages in prepare mode.
			if prepare:
				return

			# Sign all built packages with the host key (if available).
			self.sign_packages()

			# Dump package information.
			self.dump()

			return

		# End here in case of an error.
		raise BuildError(_("The build command failed. See logfile for details."))

	def install_test(self):
		self.log.info(_("Running installation test..."))

		# Install all packages that were built.
		self.install(self.find_result_packages(), allow_vendorchange=True,
			allow_uninstall=True, signatures_mode="disabled")

		self.log.info(_("Installation test succeeded."))
		self.log.info("")


	def sign_packages(self, keyfp=None):
		# Do nothing if signing is not requested.
		if not self.settings.get("sign_packages"):
			return

		# Get key, that should be used for signing.
		if not keyfp:
			keyfp = self.keyring.get_host_key_id()

		# Find all files to process.
		files = self.find_result_packages()

		# Create a progressbar.
		print(_("Signing packages..."))
		p = util.make_progress(keyfp, len(files))
		i = 0

		for file in files:
			# Update progressbar.
			if p:
				i += 1
				p.update(i)

			# Open package file.
			pkg = packages.open(self.pakfire, None, file)

			# Sign it.
			pkg.sign(keyfp)

		# Close progressbar.
		if p:
			p.finish()
			print("") # Print an empty line.

	def dump(self):
		pkgs = []

		for file in self.find_result_packages():
			pkg = packages.open(self.pakfire, None, file)
			pkgs.append(pkg)

		# If there are no packages, there is nothing to do.
		if not pkgs:
			return

		pkgs.sort()

		self.log.info(_("Dumping package information:"))
		for pkg in pkgs:
			dump = pkg.dump(int=True)

			for line in dump.splitlines():
				self.log.info("  %s" % line)
			self.log.info("") # Empty line.


class BuilderInternal(object):
	def __init__(self, pakfire, filename, resultdir, **kwargs):
		self.pakfire = pakfire

		self.filename = filename

		self.resultdir = resultdir

		# Open package file.
		self.pkg = packages.Makefile(self.pakfire, self.filename)

		self._environ = {
			"LANG"             : "C",
		}

	@property
	def buildroot(self):
		return self.pkg.buildroot

	@property
	def distro(self):
		return self.pakfire.distro

	@property
	def environ(self):
		environ = os.environ

		# Get all definitions from the package.
		environ.update(self.pkg.exports)

		# Overwrite some definitions by default values.
		environ.update(self._environ)

		return environ

	def execute(self, command, logger=None, **kwargs):
		if logger is None:
			logger = logging.getLogger("pakfire")

		# Make every shell to a login shell because we set a lot of
		# environment things there.
		command = ["bash", "--login", "-c", command]

		args = {
			"cwd"         : "/%s" % LOCAL_TMP_PATH,
			"env"         : self.environ,
			"logger"      : logger,
			"personality" : self.distro.personality,
			"shell"       : False,
		}
		args.update(kwargs)

		try:
			shellenv = shell.ShellExecuteEnvironment(command, **args)
			shellenv.execute()

		except ShellEnvironmentError:
			logger.error("Command exited with an error: %s" % command)
			raise

		return shellenv

	def run_script(self, script, *args):
		if not script.startswith("/"):
			script = os.path.join(SCRIPT_DIR, script)

		assert os.path.exists(script), "Script we should run does not exist: %s" % script

		cmd = [script,]
		for arg in args:
			cmd.append(arg)
		cmd = " ".join(cmd)

		# Returns the output of the command, but the output won't get
		# logged.
		exe = self.execute(cmd, record_output=True, log_output=False)

		# Return the output of the command.
		if exe.exitcode == 0:
			return exe.output

	def create_buildscript(self, stage):
		# Get buildscript from the package.
		script = self.pkg.get_buildscript(stage)

		# Write script to an empty file.
		f = tempfile.NamedTemporaryFile(mode="w", delete=False)
		f.write("#!/bin/sh\n\n")
		f.write("set -e\n")
		f.write("set -x\n")
		f.write("\n%s\n" % script)
		f.write("exit 0\n")
		f.close()

		# Make the script executable.
		os.chmod(f.name, 700)

		return f.name

	def build(self, stages=None):
		# Create buildroot and remove all content if it was existant.
		util.rm(self.buildroot)
		os.makedirs(self.buildroot)

		# Process stages in order.
		for stage in ("prepare", "build", "test", "install"):
			# Skip unwanted stages.
			if stages and not stage in stages:
				continue

			# Run stage.
			self.build_stage(stage)

		# Stop if install stage has not been processed.
		if stages and not "install" in stages:
			return

		# Run post-build stuff.
		self.post_compress_man_pages()
		self.post_remove_static_libs()
		self.post_extract_debuginfo()

		# Package the result.
		# Make all these little package from the build environment.
		log.info(_("Creating packages:"))
		pkgs = []
		for pkg in reversed(self.pkg.packages):
			packager = packages.packager.BinaryPackager(self.pakfire, pkg,
				self, self.buildroot)
			pkg = packager.run(self.resultdir)
			pkgs.append(pkg)
		log.info("")

	def build_stage(self, stage):
		# Get the buildscript for this stage.
		buildscript = self.create_buildscript(stage)

		# Execute the buildscript of this stage.
		log.info(_("Running stage %s:") % stage)

		try:
			self.execute(buildscript)

		finally:
			# Remove the buildscript.
			if os.path.exists(buildscript):
				os.unlink(buildscript)

	def post_remove_static_libs(self):
		keep_libs = self.pkg.lexer.build.get_var("keep_libraries")
		keep_libs = keep_libs.split()

		try:
			self.execute("%s/remove-static-libs %s %s" % \
				(SCRIPT_DIR, self.buildroot, " ".join(keep_libs)))
		except ShellEnvironmentError as e:
			log.warning(_("Could not remove static libraries: %s") % e)

	def post_compress_man_pages(self):
		try:
			self.execute("%s/compress-man-pages %s" % (SCRIPT_DIR, self.buildroot))
		except ShellEnvironmentError as e:
			log.warning(_("Compressing man pages did not complete successfully."))

	def post_extract_debuginfo(self):
		args = []

		# Check if we need to run with strict build-id.
		strict_id = self.pkg.lexer.build.get_var("debuginfo_strict_build_id", "true")
		if strict_id in ("true", "yes", "1"):
			args.append("--strict-build-id")

		args.append("--buildroot=%s" % self.pkg.buildroot)
		args.append("--sourcedir=%s" % self.pkg.sourcedir)

		# Get additional options to pass to script.
		options = self.pkg.lexer.build.get_var("debuginfo_options", "")
		args += options.split()

		try:
			self.execute("%s/extract-debuginfo %s %s" % (SCRIPT_DIR, " ".join(args), self.pkg.buildroot))
		except ShellEnvironmentError as e:
			log.error(_("Extracting debuginfo did not complete with success. Aborting build."))
			raise

	def find_prerequires(self, scriptlet_file):
		assert os.path.exists(scriptlet_file), "Scriptlet file does not exist: %s" % scriptlet_file

		res = self.run_script("find-prerequires", scriptlet_file)
		prerequires = set(res.splitlines())

		return prerequires

	def cleanup(self):
		if os.path.exists(self.buildroot):
			util.rm(self.buildroot)
