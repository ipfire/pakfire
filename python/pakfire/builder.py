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
import grp
import math
import os
import re
import shutil
import socket
import time
import uuid

import base
import chroot
import logger
import packages
import packages.file
import packages.packager
import repository
import util
import _pakfire

import logging
log = logging.getLogger("pakfire")

from config import ConfigBuilder
from system import system
from constants import *
from i18n import _
from errors import BuildError, BuildRootLocked, Error


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

class BuildEnviron(object):
	# The version of the kernel this machine is running.
	kernel_version = os.uname()[2]

	def __init__(self, filename=None, distro_name=None, config=None, configs=None, arch=None,
			build_id=None, logfile=None, builder_mode="release", use_cache=None, **pakfire_args):
		# Set mode.
		assert builder_mode in ("development", "release",)
		self.mode = builder_mode

		# Disable the build repository in release mode.
		if self.mode == "release":
			if pakfire_args.has_key("disable_repos") and pakfire_args["disable_repos"]:
				pakfire_args["disable_repos"] += ["build",]
			else:
				pakfire_args["disable_repos"] = ["build",]

		# Save the build id and generate one if no build id was provided.
		if not build_id:
			build_id = "%s" % uuid.uuid4()

		self.build_id = build_id

		# Setup the logging.
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

		# Log information about pakfire and some more information, when we
		# are running in release mode.
		if self.mode == "release":
			logdata = {
				"host_arch"  : system.arch,
				"hostname"   : system.hostname,
				"time"       : time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()),
				"version"    : "Pakfire %s" % PAKFIRE_VERSION,
			}

			for line in BUILD_LOG_HEADER.splitlines():
				self.log.info(line % logdata)

		# Create pakfire instance.
		if pakfire_args.has_key("mode"):
			del pakfire_args["mode"]

		if config is None:
			config = ConfigBuilder(files=configs)

			if not configs:
				if distro_name is None:
					distro_name = config.get("builder", "distro", None)
				config.load_distro_config(distro_name)

		if not config.has_distro():
			log.error(_("You have not set the distribution for which you want to build."))
			log.error(_("Please do so in builder.conf or on the CLI."))
			raise ConfigError, _("Distribution configuration is missing.")

		self.pakfire = base.Pakfire(
			mode="builder",
			config=config,
			arch=arch,
			**pakfire_args
		)

		self.distro = self.pakfire.distro
		self.path = self.pakfire.path

		# Check if this host can build the requested architecture.
		if not system.host_supports_arch(self.arch):
			raise BuildError, _("Cannot build for %s on this host.") % self.arch

		# Where do we put the result?
		self.resultdir = os.path.join(self.path, "result")

		# Check weather to use or not use the cache.
		if use_cache is None:
			# If use_cache is None, the user did not provide anything and
			# so we guess.
			if self.mode == "development":
				use_cache = True
			else:
				use_cache = False

		self.use_cache = use_cache

		# Open package.
		# If we have a plain makefile, we first build a source package and go with that.
		if filename:
			if filename.endswith(".%s" % MAKEFILE_EXTENSION):
				pkg = packages.Makefile(self.pakfire, filename)
				filename = pkg.dist(os.path.join(self.resultdir, "src"))

				assert os.path.exists(filename), filename

			# Open source package.
			self.pkg = packages.SourcePackage(self.pakfire, None, filename)
			assert self.pkg, filename

			# Log the package information.
			self.log.info(_("Package information:"))
			for line in self.pkg.dump(long=True).splitlines():
				self.log.info("  %s" % line)
			self.log.info("")

			# Path where we extract the package and put all the source files.
			self.build_dir = os.path.join(self.path, "usr/src/packages", self.pkg.friendly_name)
		else:
			# No package :(
			self.pkg = None

		# XXX need to make this configureable
		self.settings = {
			"enable_loop_devices" : True,
			"enable_ccache"   : True,
			"enable_icecream" : False,
			"sign_packages"   : True,
		}
		#self.settings.update(settings)

		# Lock the buildroot
		self._lock = None
		self.lock()

		# Save the build time.
		self.build_time = int(time.time())

	def start(self):
		# Mount the directories.
		self._mountall()

		# Populate /dev.
		self.populate_dev()

		# Setup domain name resolution in chroot.
		self.setup_dns()

		# Extract all needed packages.
		self.extract()

	def stop(self):
		# Kill all still running processes.
		util.orphans_kill(self.path)

		# Close pakfire instance.
		del self.pakfire

		# Umount the build environment.
		self._umountall()

		# Remove all files.
		self.destroy()

	@property
	def arch(self):
		"""
			Inherit architecture from distribution configuration.
		"""
		return self.distro.arch

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

			(Makes also sure that it is properly initialized.)
		"""
		assert self.pakfire

		if not self.pakfire.keyring.initialized:
			self.pakfire.keyring.init()

		return self.pakfire.keyring

	def lock(self):
		filename = os.path.join(self.path, ".lock")

		try:
			self._lock = open(filename, "a+")
		except IOError, e:
			return 0

		try:
			fcntl.lockf(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
		except IOError, e:
			raise BuildRootLocked, "Buildroot is locked"

		return 1

	def unlock(self):
		if self._lock:
			self._lock.close()
			self._lock = None

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

	def extract(self, requires=None, build_deps=True):
		"""
			Gets a dependency set and extracts all packages
			to the environment.
		"""
		if not requires:
			requires = []

		if self.use_cache and os.path.exists(self.cache_file):
			# If we are told to use the cache, we just import the
			# file.
			self.cache_extract()
		else:
			# Add neccessary build dependencies.
			requires += BUILD_PACKAGES

		# If we have ccache enabled, we need to extract it
		# to the build chroot.
		if self.settings.get("enable_ccache"):
			requires.append("ccache")

		# If we have icecream enabled, we need to extract it
		# to the build chroot.
		if self.settings.get("enable_icecream"):
			requires.append("icecream")

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

	def install(self, requires):
		"""
			Install everything that is required in requires.
		"""
		# If we got nothing to do, we quit immediately.
		if not requires:
			return

		try:
			self.pakfire.install(requires, interactive=False,
				allow_downgrade=True, logger=self.log)

		# Catch dependency errors and log it.
		except DependencyError, e:
			raise

	def install_test(self):
		try:
			self.pakfire.localinstall(self.find_result_packages(), yes=True, allow_uninstall=True, logger=self.log)

		# Dependency errors when trying to install the result packages are build errors.
		except DependencyError, e:
			# Dump all packages (for debugging).
			self.dump()

			raise BuildError, e

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
			node_stat = os.stat(node)

			self._create_node(node, node_stat.st_mode, node_stat.st_rdev)

		os.symlink("/proc/self/fd/0", self.chrootPath("dev", "stdin"))
		os.symlink("/proc/self/fd/1", self.chrootPath("dev", "stdout"))
		os.symlink("/proc/self/fd/2", self.chrootPath("dev", "stderr"))
		os.symlink("/proc/self/fd",   self.chrootPath("dev", "fd"))

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

	def destroy(self):
		self.log.debug("Destroying environment %s" % self.path)

		if os.path.exists(self.path):
			util.rm(self.path)

	def cleanup(self):
		self.log.debug("Cleaning environemnt.")

		# Remove the build directory and buildroot.
		dirs = (self.build_dir, self.chrootPath("result"),)

		for d in dirs:
			if not os.path.exists(d):
				continue

			util.rm(d)
			os.makedirs(d)

	def _mountall(self):
		self.log.debug("Mounting environment")
		for src, dest, fs, options in self.mountpoints:
			mountpoint = self.chrootPath(dest)
			if options:
				options = "-o %s" % options

			# Eventually create mountpoint directory
			if not os.path.exists(mountpoint):
				os.makedirs(mountpoint)

			cmd = "mount -n -t %s %s %s %s" % \
				(fs, options, src, mountpoint)
			chroot.do(cmd, shell=True)

	def _umountall(self):
		self.log.debug("Umounting environment")

		mountpoints = []
		for src, dest, fs, options in reversed(self.mountpoints):
			if not dest in mountpoints:
				mountpoints.append(dest)

		for dest in mountpoints:
			mountpoint = self.chrootPath(dest)

			chroot.do("umount -n %s" % mountpoint, raiseExc=0, shell=True)

	@property
	def mountpoints(self):
		mountpoints = []

		# Make root as a tmpfs.
		#mountpoints += [
		#	("pakfire_root", "/", "tmpfs", "defaults"),
		#]

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

	@property
	def environ(self):
		env = {
			# Add HOME manually, because it is occasionally not set
			# and some builds get in trouble then.
			"HOME" : "/root",
			"TERM" : os.environ.get("TERM", "dumb"),
			"PS1"  : "\u:\w\$ ",

			# Sanitize language.
			"LANG" : os.environ.setdefault("LANG", "en_US.UTF-8"),

			# Set the container that we can detect, if we are inside a
			# chroot.
			"container" : "pakfire-builder",
		}

		# Inherit environment from distro
		env.update(self.pakfire.distro.environ)

		# Icecream environment settings
		if self.settings.get("enable_icecream", False):
			# Set the toolchain path
			if self.settings.get("icecream_toolchain", None):
				env["ICECC_VERSION"] = self.settings.get("icecream_toolchain")

			# Set preferred host if configured.
			if self.settings.get("icecream_preferred_host", None):
				env["ICECC_PREFERRED_HOST"] = \
					self.settings.get("icecream_preferred_host")

		# Fake UTS_MACHINE, when we cannot use the personality syscall and
		# if the host architecture is not equal to the target architecture.
		if not self.pakfire.distro.personality and \
				not system.native_arch == self.pakfire.distro.arch:
			env.update({
				"LD_PRELOAD"  : "/usr/lib/libpakfire_preload.so",
				"UTS_MACHINE" : self.pakfire.distro.arch,
			})

		return env

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

	def do(self, command, shell=True, personality=None, logger=None, *args, **kwargs):
		ret = None

		# Environment variables
		env = self.environ

		if kwargs.has_key("env"):
			env.update(kwargs.pop("env"))

		self.log.debug("Environment:")
		for k, v in sorted(env.items()):
			self.log.debug("  %s=%s" % (k, v))

		# Update personality it none was set
		if not personality:
			personality = self.distro.personality

		# Make every shell to a login shell because we set a lot of
		# environment things there.
		if shell:
			command = ["bash", "--login", "-c", command]

		if not kwargs.has_key("chrootPath"):
			kwargs["chrootPath"] = self.chrootPath()

		ret = chroot.do(
			command,
			personality=personality,
			shell=False,
			env=env,
			logger=logger,
			*args,
			**kwargs
		)

		return ret

	def build(self, install_test=True):
		if not self.pkg:
			raise BuildError, _("You cannot run a build when no package was given.")

		# Search for the package file in build_dir and raise BuildError if it is not present.
		pkgfile = os.path.join(self.build_dir, "%s.%s" % (self.pkg.name, MAKEFILE_EXTENSION))
		if not os.path.exists(pkgfile):
			raise BuildError, _("Could not find makefile in build root: %s") % pkgfile
		pkgfile = "/%s" % os.path.relpath(pkgfile, self.chrootPath())

		# Write pakfire configuration into the chroot.
		self.write_config()

		# Create the build command, that is executed in the chroot.
		build_command = [
			"/usr/lib/pakfire/builder",
			"--offline",
			"build",
			pkgfile,
			"--arch", self.arch,
			"--nodeps",
			"--resultdir=/result",
		]

		try:
			self.do(" ".join(build_command), logger=self.log)

		except Error:
			self.log.error(_("Build failed."), exc_info=True)

			raise BuildError, _("The build command failed. See logfile for details.")

		# Sign all built packages with the host key (if available).
		if self.settings.get("sign_packages"):
			host_key = self.keyring.get_host_key()
			assert host_key

			# Do the signing...
			self.sign(host_key)

		# Perform install test.
		if install_test:
			self.install_test()

		# Dump package information.
		self.dump()

	def shell(self, args=[]):
		if not util.cli_is_interactive():
			self.log.warning("Cannot run shell on non-interactive console.")
			return

		# Install all packages that are needed to run a shell.
		self.install(SHELL_PACKAGES)

		# XXX need to set CFLAGS here
		command = "/usr/sbin/chroot %s %s %s" % \
			(self.chrootPath(), SHELL_SCRIPT, " ".join(args))

		# Add personality if we require one
		if self.pakfire.distro.personality:
			command = "%s %s" % (self.pakfire.distro.personality, command)

		for key, val in self.environ.items():
			command = "%s=\"%s\" " % (key, val) + command

		# Empty the environment
		command = "env -i - %s" % command

		self.log.debug("Shell command: %s" % command)

		shell = os.system(command)
		return os.WEXITSTATUS(shell)

	def sign(self, keyfp):
		assert self.keyring.get_key(keyfp), "Key for signing does not exist"

		# Find all files to process.
		files = self.find_result_packages()

		# Create a progressbar.
		p = util.make_progress(_("Signing files (%s)") % keyfp, len(files))
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
			dump = pkg.dump(long=True)

			for line in dump.splitlines():
				self.log.info("  %s" % line)
			self.log.info("") # Empty line.

	@property
	def cache_file(self):
		comps = [
			self.pakfire.distro.sname,	# name of the distribution
			self.pakfire.distro.release,	# release version
			self.pakfire.distro.arch,	# architecture
		]

		return os.path.join(CACHE_ENVIRON_DIR, "%s.cache" %"-".join(comps))

	def cache_export(self, filename):
		# Sync all disk caches.
		_pakfire.sync()

		# A list to store all mountpoints, so we don't package them.
		mountpoints = []

		# A list containing all files we want to package.
		filelist = []

		# Walk through the whole tree and collect all files
		# that are on the same disk (not crossing mountpoints).
		log.info(_("Creating filelist..."))
		root = self.chrootPath()
		for dir, subdirs, files in os.walk(root):
			# Search for mountpoints and skip them.
			if not dir == root and os.path.ismount(dir):
				mountpoints.append(dir)
				continue

			# Skip all directories under mountpoints.
			if any([dir.startswith(m) for m in mountpoints]):
				continue

			# Add all other files.
			filelist.append(dir)
			for file in files:
				file = os.path.join(dir, file)
				filelist.append(file)

		# Create a nice progressbar.
		p = util.make_progress(_("Compressing files..."), len(filelist))
		i = 0

		# Create tar file and add all files to it.
		f = packages.file.InnerTarFile.open(filename, "w:gz")
		for file in filelist:
			i += 1
			if p:
				p.update(i)

			f.add(file, os.path.relpath(file, root), recursive=False)
		f.close()

		# Finish progressbar.
		if p:
			p.finish()

		filesize = os.path.getsize(filename)

		log.info(_("Cache file was successfully created at %s.") % filename)
		log.info(_("  Containing %(files)s files, it has a size of %(size)s.") % \
			{ "files" : len(filelist), "size" : util.format_size(filesize), })

	def cache_extract(self):
		root = self.chrootPath()
		filename = self.cache_file

		f = packages.file.InnerTarFile.open(filename, "r:gz")
		members = f.getmembers()

		# Make a nice progress bar as always.
		p = util.make_progress(_("Extracting files..."), len(members))

		# Extract all files from the cache.
		i = 0
		for member in members:
			if p:
				i += 1
				p.update(i)

			f.extract(member, path=root)
		f.close()

		# Finish progressbar.
		if p:
			p.finish()

		# Re-read local repository.
		self.pakfire.repos.local.update(force=True)

		# Update all packages.
		self.log.info(_("Updating packages from cache..."))
		self.pakfire.update(interactive=False, logger=self.log,
			allow_archchange=True, allow_vendorchange=True, allow_downgrade=True)


class Builder(object):
	def __init__(self, pakfire, filename, resultdir, **kwargs):
		self.pakfire = pakfire

		self.filename = filename

		self.resultdir = resultdir

		# Open package file.
		self.pkg = packages.Makefile(self.pakfire, self.filename)

		self._environ = {
			"LANG"             : "C",
		}

	def mktemp(self):
		"""
			Create a temporary file in the build environment.
		"""
		file = "/tmp/pakfire_%s" % util.random_string()

		# Touch the file.
		f = open(file, "w")
		f.close()

		return file

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

	def do(self, command, shell=True, personality=None, cwd=None, *args, **kwargs):
		# Environment variables
		log.debug("Environment:")
		for k, v in sorted(self.environ.items()):
			log.debug("  %s=%s" % (k, v))

		# Update personality it none was set
		if not personality:
			personality = self.distro.personality

		if not cwd:
			cwd = "/%s" % LOCAL_TMP_PATH

		# Make every shell to a login shell because we set a lot of
		# environment things there.
		if shell:
			command = ["bash", "--login", "-c", command]

		return chroot.do(
			command,
			personality=personality,
			shell=False,
			env=self.environ,
			logger=logging.getLogger("pakfire"),
			cwd=cwd,
			*args,
			**kwargs
		)

	def create_icecream_toolchain(self):
		try:
			out = self.do("icecc --build-native 2>/dev/null", returnOutput=True, cwd="/tmp")
		except Error:
			return

		for line in out.splitlines():
			m = re.match(r"^creating ([a-z0-9]+\.tar\.gz)", line)
			if m:
				self._environ["ICECC_VERSION"] = "/tmp/%s" % m.group(1)

	def create_buildscript(self, stage):
		file = "/tmp/build_%s" % util.random_string()

		# Get buildscript from the package.
		script = self.pkg.get_buildscript(stage)

		# Write script to an empty file.
		f = open(file, "w")
		f.write("#!/bin/sh\n\n")
		f.write("set -e\n")
		f.write("set -x\n")
		f.write("\n%s\n" % script)
		f.write("exit 0\n")
		f.close()
		os.chmod(file, 700)

		return file

	def build(self):
		# Create buildroot and remove all content if it was existant.
		util.rm(self.buildroot)
		os.makedirs(self.buildroot)

		# Build icecream toolchain if icecream is installed.
		self.create_icecream_toolchain()

		for stage in ("prepare", "build", "test", "install"):
			self.build_stage(stage)

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
			self.do(buildscript, shell=False)

		finally:
			# Remove the buildscript.
			if os.path.exists(buildscript):
				os.unlink(buildscript)

	def post_remove_static_libs(self):
		keep_libs = self.pkg.lexer.build.get_var("keep_libraries")
		keep_libs = keep_libs.split()

		try:
			self.do("%s/remove-static-libs %s %s" % \
				(SCRIPT_DIR, self.buildroot, " ".join(keep_libs)))
		except Error, e:
			log.warning(_("Could not remove static libraries: %s") % e)

	def post_compress_man_pages(self):
		try:
			self.do("%s/compress-man-pages %s" % (SCRIPT_DIR, self.buildroot))
		except Error, e:
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
			self.do("%s/extract-debuginfo %s %s" % (SCRIPT_DIR, " ".join(args), self.pkg.buildroot))
		except Error, e:
			log.error(_("Extracting debuginfo did not complete with success. Aborting build."))
			raise

	def cleanup(self):
		if os.path.exists(self.buildroot):
			util.rm(self.buildroot)
