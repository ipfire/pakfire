#!/usr/bin/python

import fcntl
import grp
import logging
import math
import os
import re
import shutil
import socket
import stat
import time
import uuid

import depsolve
import packages
import repository
import transaction
import util

from constants import *
from errors import BuildError, BuildRootLocked, Error


class Builder(object):
	# The version of the kernel this machine is running.
	kernel_version = os.uname()[2]

	def __init__(self, pakfire, pkg, build_id=None, **settings):
		self.pakfire = pakfire
		self.pkg = pkg

		self.settings = {
			"enable_loop_devices" : True,
			"enable_ccache"   : True,
			"enable_icecream" : False,
		}
		self.settings.update(settings)

		self.buildroot = "/buildroot"

		# Lock the buildroot
		self._lock = None
		self.lock()

		# Save the build time.
		self.build_time = int(time.time())

		# Save the build id and generate one if no build id was provided.
		if not build_id:
			build_id = uuid.uuid4()

		self.build_id = build_id

	@property
	def info(self):
		return {
			"build_date" : time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(self.build_time)),
			"build_host" : socket.gethostname(),
			"build_id"   : self.build_id,
			"build_time" : self.build_time,
		}

	@property
	def path(self):
		return self.pakfire.path

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

		logging.debug("%s --> %s" % (file_out, file_in))

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

		logging.debug("%s --> %s" % (file_in, file_out))

		shutil.copy2(file_in, file_out)

	def copy_result(self, resultdir):
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

	def extract(self, requires=None, build_deps=True):
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

		# If we have icecream enabled, we need to extract it
		# to the build chroot.
		if self.settings.get("enable_icecream"):
			requires.append("icecream")

		# Get build dependencies from source package.
		if isinstance(self.pkg, packages.SourcePackage):
			for req in self.pkg.requires:
				requires.append(req)

		# Install all packages.
		self.install(requires)

		# Copy the makefile and load source tarballs.
		if isinstance(self.pkg, packages.Makefile):
			self.pkg.extract(self)

		# If we have a makefile, we can only get the build dependencies
		# after we have extracted all the rest.
		if build_deps and isinstance(self.pkg, packages.Makefile):
			requires = self.make_requires()
			if not requires:
				return

			self.install(requires)

	def install(self, requires):
		"""
			Install everything that is required in requires.
		"""
		ds = depsolve.DependencySet(self.pakfire)
		for r in requires:
			ds.add_requires(r)
		ds.resolve()
		ds.dump()

		ts = transaction.Transaction(self.pakfire, ds)
		ts.run()

	@property
	def log(self):
		# XXX for now, return the root logger
		return logging.getLogger()

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

	def prepare(self):
		# Create directory.
		if not os.path.exists(self.path):
			os.makedirs(self.path)

		# Create important directories.
		dirs = [
			"build",
			self.buildroot,
			"dev",
			"dev/pts",
			"dev/shm",
			"etc",
			"proc",
			"result",
			"sys",
			"tmp",
			"usr/src",
		]

		# Create cache dir if ccache is enabled.
		if self.settings.get("enable_ccache"):
			dirs.append("var/cache/ccache")

			if not os.path.exists(CCACHE_CACHE_DIR):
				os.makedirs(CCACHE_CACHE_DIR)

		for dir in dirs:
			dir = self.chrootPath(dir)
			if not os.path.exists(dir):
				os.makedirs(dir)

		# Create neccessary files like /etc/fstab and /etc/mtab.
		files = (
			"etc/fstab",
			"etc/mtab"
		)

		for file in files:
			file = self.chrootPath(file)
			dir = os.path.dirname(file)
			if not os.path.exists(dir):
				os.makedirs(dir)
			f = open(file, "w")
			f.close()

		self._prepare_dev()
		self._prepare_users()
		self._prepare_dns()

	def _prepare_dev(self):
		prevMask = os.umask(0000)

		nodes = [
			("dev/null",	stat.S_IFCHR | 0666, os.makedev(1, 3)),
			("dev/full",	stat.S_IFCHR | 0666, os.makedev(1, 7)),
			("dev/zero",	stat.S_IFCHR | 0666, os.makedev(1, 5)),
			("dev/random",	stat.S_IFCHR | 0666, os.makedev(1, 8)),
			("dev/urandom",	stat.S_IFCHR | 0444, os.makedev(1, 9)),
			("dev/tty",		stat.S_IFCHR | 0666, os.makedev(5, 0)),
			("dev/console",	stat.S_IFCHR | 0600, os.makedev(5, 1)),
		]

		# If we need loop devices (which are optional) we create them here.
		if self.settings["enable_loop_devices"]:
			for i in range(0, 7):
				nodes.append(("dev/loop%d" % i, stat.S_IFBLK | 0660, os.makedev(7, i)))

		# Create all the nodes.
		for node in nodes:
			self._create_node(*node)

		os.symlink("/proc/self/fd/0", self.chrootPath("dev", "stdin"))
		os.symlink("/proc/self/fd/1", self.chrootPath("dev", "stdout"))
		os.symlink("/proc/self/fd/2", self.chrootPath("dev", "stderr"))
		os.symlink("/proc/self/fd",   self.chrootPath("dev", "fd"))

		# make device node for el4 and el5
		if self.kernel_version < "2.6.19":
			self._make_node("dev/ptmx", stat.S_IFCHR | 0666, os.makedev(5, 2))
		else:
			os.symlink("/dev/pts/ptmx", self.chrootPath("dev", "ptmx"))

		os.umask(prevMask)

	def _prepare_users(self):
		f = open(self.chrootPath("etc", "passwd"), "w")
		f.write("root:x:0:0:root:/root:/bin/bash\n")
		f.write("nobody:x:99:99:Nobody:/:/sbin/nologin\n")
		f.close()

		f = open(self.chrootPath("etc", "group"), "w")
		f.write("root:x:0:root\n")
		f.write("nobody:x:99:\n")
		f.close()

	def _prepare_dns(self):
		"""
			Add DNS resolution facility to chroot environment by copying
			/etc/resolv.conf and /etc/hosts.
		"""
		for i in ("/etc/resolv.conf", "/etc/hosts"):
			self.copyin(i, i)

	def _create_node(self, filename, mode, device):
		logging.debug("Create node: %s (%s)" % (filename, mode))

		filename = self.chrootPath(filename)

		# Create parent directory if it is missing.
		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		os.mknod(filename, mode, device)

	def destroy(self):
		logging.debug("Cleanup environment %s" % self.path)

		if os.path.exists(self.path):
			util.rm(self.path)

	def _mountall(self):
		self.log.debug("Mounting environment")
		for cmd, mountpoint in self.mountpoints:
			cmd = "%s %s" % (cmd, self.chrootPath(mountpoint))
			util.do(cmd, shell=True)

	def _umountall(self):
		self.log.debug("Umounting environment")
		for cmd, mountpoint in self.mountpoints:
			cmd = "umount -n %s" % self.chrootPath(mountpoint)
			util.do(cmd, raiseExc=0, shell=True)

	@property
	def mountpoints(self):
		ret = [
			("mount -n -t proc pakfire_chroot_proc", "proc"),
			("mount -n -t sysfs pakfire_chroot_sysfs", "sys"),
		]

		mountopt = "gid=%d,mode=0620,ptmxmode=0666" % grp.getgrnam("tty").gr_gid
		if self.kernel_version >= "2.6.29":
			mountopt += ",newinstance"

		ret.extend([
			("mount -n -t devpts -o %s pakfire_chroot_devpts" % mountopt, "dev/pts"),
			("mount -n -t tmpfs pakfire_chroot_shmfs", "dev/shm"),
		])

		if self.settings.get("enable_ccache"):
			ret.append(("mount -n --bind %s" % CCACHE_CACHE_DIR, "var/cache/ccache"))

		return ret

	@staticmethod
	def calc_parallelism():
		"""
			Calculate how many processes to run
			at the same time.

			We take the log10(number of processors) * factor
		"""
		num = os.sysconf("SC_NPROCESSORS_CONF")
		if num == 1:
			return 2
		else:
			return int(round(math.log10(num) * 26))

	@property
	def environ(self):
		env = {
			# Add HOME manually, because it is occasionally not set
			# and some builds get in trouble then.
			"HOME" : "/root",
			"TERM" : os.environ.get("TERM", "dumb"),
			"PS1"  : "\u:\w\$ ",

			"BUILDROOT" : self.buildroot,
			"PARALLELISMFLAGS" : "-j%s" % self.calc_parallelism(),
		}

		# Inherit environment from distro
		env.update(self.pakfire.distro.environ)

		# Icecream environment settings
		if self.settings.get("enable_icecream", None):
			# Set the toolchain path
			if self.settings.get("icecream_toolchain", None):
				env["ICECC_VERSION"] = self.settings.get("icecream_toolchain")

			# Set preferred host if configured.
			if self.settings.get("icecream_preferred_host", None):
				env["ICECC_PREFERRED_HOST"] = \
					self.settings.get("icecream_preferred_host")

		# XXX what do we need else?

		return env

	def do(self, command, shell=True, personality=None, *args, **kwargs):
		ret = None
		try:
			# Environment variables
			env = self.environ

			if kwargs.has_key("env"):
				env.update(kwargs.pop("env"))

			logging.debug("Environment:")
			for k, v in sorted(env.items()):
				logging.debug("  %s=%s" % (k, v))

			# Update personality it none was set
			if not personality:
				personality = self.pakfire.distro.personality

			# Make every shell to a login shell because we set a lot of
			# environment things there.
			if shell:
				command = ["bash", "--login", "-c", command]

			self._mountall()

			if not kwargs.has_key("chrootPath"):
				kwargs["chrootPath"] = self.chrootPath()

			ret = util.do(
				command,
				personality=personality,
				shell=False,
				env=env,
				logger=self.log,
				*args,
				**kwargs
			)

		finally:
			self._umountall()

		return ret

	def make(self, *args, **kwargs):
		return self.do("make -f /build/%s %s" % \
			(os.path.basename(self.pkg.filename), " ".join(args)),
			**kwargs)

	@property
	def make_info(self):
		if not hasattr(self, "_make_info"):
			info = {}

			output = self.make("buildinfo", returnOutput=True)

			for line in output.splitlines():
				# XXX temporarily
				if not line:
					break

				m = re.match(r"^(\w+)=(.*)$", line)
				if not m:
					continue

				info[m.group(1)] = m.group(2).strip("\"")

			self._make_info = info

		return self._make_info

	@property
	def packages(self):
		if hasattr(self, "_packages"):
			return self._packages

		pkgs = []
		output = self.make("packageinfo", returnOutput=True)

		pkg = {}
		for line in output.splitlines():
			if not line:
				pkgs.append(pkg)
				pkg = {}

			m = re.match(r"^(\w+)=(.*)$", line)
			if not m:
				continue

			k, v = m.groups()
			pkg[k] = v.strip("\"")

		# Create a dummy repository to link the virtual packages to
		repo = repository.DummyRepository(self.pakfire)

		self._packages = []
		for pkg in pkgs:
			pkg = packages.VirtualPackage(self.pakfire, pkg) # XXX had to remove repo here?!
			self._packages.append(pkg)

		return self._packages

	def make_requires(self):
		return self.make_info.get("PKG_BUILD_DEPS", "").split()

	def make_sources(self):
		return self.make_info.get("PKG_FILES", "").split()

	def create_icecream_toolchain(self):
		if not self.settings.get("enable_icecream", None):
			return

		out = self.do("icecc --build-native", returnOutput=True)

		for line in out.splitlines():
			m = re.match(r"^creating ([a-z0-9]+\.tar\.gz)", line)
			if m:
				self.settings["icecream_toolchain"] = "/%s" % m.group(1)

	def build(self):
		self.create_icecream_toolchain()

		try:
			self.make("build")

		except Error:
			raise BuildError, "The build command failed."

		for pkg in reversed(self.packages):
			packager = packages.Packager(self.pakfire, pkg, self)
			packager()

	def dist(self):
		self.pkg.dist(self)

	def shell(self, args=[]):
		if not util.cli_is_interactive():
			logging.warning("Cannot run shell on non-interactive console.")
			return

		# Install all packages that are needed to run a shell.
		self.install(SHELL_PACKAGES)

		# XXX need to set CFLAGS here
		command = "/usr/sbin/chroot %s /usr/bin/chroot-shell %s" % \
			(self.chrootPath(), " ".join(args))

		# Add personality if we require one
		if self.pakfire.distro.personality:
			command = "%s %s" % (self.pakfire.distro.personality, command)

		for key, val in self.environ.items():
			command = "%s=\"%s\" " % (key, val) + command

		# Empty the environment
		command = "env -i - %s" % command

		logging.debug("Shell command: %s" % command)

		try:
			self._mountall()

			shell = os.system(command)
			return os.WEXITSTATUS(shell)

		finally:
			self._umountall()
