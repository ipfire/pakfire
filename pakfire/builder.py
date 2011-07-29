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

import base
import chroot
import logger
import packages
import repository
import util

from constants import *
from i18n import _
from errors import BuildError, BuildRootLocked, Error


BUILD_LOG_HEADER = """
 ____       _     __ _            _           _ _     _
|  _ \ __ _| | __/ _(_)_ __ ___  | |__  _   _(_) | __| | ___ _ __
| |_) / _` | |/ / |_| | '__/ _ \ | '_ \| | | | | |/ _` |/ _ \ '__|
|  __/ (_| |   <|  _| | | |  __/ | |_) | |_| | | | (_| |  __/ |
|_|   \__,_|_|\_\_| |_|_|  \___| |_.__/ \__,_|_|_|\__,_|\___|_|

	Time    : %(time)s
	Host    : %(host)s
	Version : %(version)s

"""

class Builder(object):
	# The version of the kernel this machine is running.
	kernel_version = os.uname()[2]

	def __init__(self, pkg=None, distro_config=None, build_id=None, logfile=None,
			builder_mode="release", **pakfire_args):
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
			self.log = logging.getLogger(self.build_id)
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
			self.log = logging.getLogger()

		logdata = {
			"host"    : socket.gethostname(),
			"time"    : time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()),
			"version" : "Pakfire %s" % PAKFIRE_VERSION,
		}
		for line in BUILD_LOG_HEADER.splitlines():
			self.log.info(line % logdata)

		# Create pakfire instance.
		if pakfire_args.has_key("mode"):
			del pakfire_args["mode"]
		self.pakfire = base.Pakfire(mode="builder", distro_config=distro_config, **pakfire_args)
		self.distro = self.pakfire.distro
		self.path = self.pakfire.path

		# Open the package.
		self.pkg = pkg

		# XXX need to make this configureable
		self.settings = {
			"enable_loop_devices" : True,
			"enable_ccache"   : True,
			"enable_icecream" : False,
		}
		#self.settings.update(settings)

		self.buildroot = "/buildroot"

		# Lock the buildroot
		self._lock = None
		self.lock()

		# Save the build time.
		self.build_time = int(time.time())

	def get_pkg(self):
		return getattr(self, "_pkg", None)

	def set_pkg(self, pkg):
		if pkg is None:
			self.__pkg = None
			return

		self._pkg = packages.open(self.pakfire, None, pkg)

		# Log the package information.
		if not isinstance(self._pkg, packages.Makefile):
			self.log.info("Package information:")
			for line in self._pkg.dump(long=True).splitlines():
				self.log.info("  %s" % line)
			self.log.info("")

		assert self.pkg

	pkg = property(get_pkg, set_pkg)

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

		elif isinstance(self.pkg, packages.SourcePackage):
			self.pkg.extract(_("Extracting: %s (source)") % self.pkg.name,
				prefix=os.path.join(self.path, "build"))

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
		# If we got nothing to do, we quit immediately.
		if not requires:
			return

		# Create a request and fill it with what we need.
		request = self.pakfire.create_request()

		for req in requires:
			if isinstance(req, packages.BinaryPackage):
				req = req.friendly_name

			if "<" in req or ">" in req or "=" in req or req.startswith("/"):
				req = self.pakfire.create_relation(req)

			request.install(req)

		# Create a new solver instance.
		solver = self.pakfire.create_solver()

		# Do the solving.
		transaction = solver.solve(request, allow_downgrade=True)

		# XXX check for errors
		if not transaction:
			raise DependencyError, "Could not resolve dependencies"

		# Show the user what is going to be done.
		transaction.dump(logger=self.log)

		# Run the transaction.
		transaction.run()

	def install_test(self):
		# XXX currently disabled
		return

		pkgs = []
		for dir, subdirs, files in os.walk(self.chrootPath("result")):
			for file in files:
				pkgs.append(os.path.join(dir, file))

		self.pakfire.localinstall(pkgs)

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
		prepared_tag = ".prepared"

		if os.path.exists(self.chrootPath(prepared_tag)):
			return

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
			"etc/mtab",
			prepared_tag,
		)

		for file in files:
			file = self.chrootPath(file)
			dir = os.path.dirname(file)
			if not os.path.exists(dir):
				os.makedirs(dir)
			f = open(file, "w")
			f.close()

		self._prepare_dev()
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
		logging.debug("Destroying environment %s" % self.path)

		if os.path.exists(self.path):
			util.rm(self.path)

	def cleanup(self):
		logging.debug("Cleaning environemnt.")

		# Run make clean and let it cleanup its stuff.
		self.make("clean")

		# Remove the build directory and buildroot.
		dirs = ("build", self.buildroot, "result")

		for d in dirs:
			d = self.chrootPath(d)
			if not os.path.exists(d):
				continue

			util.rm(d)
			os.makedirs(d)

		# Clear make_info cache.
		if hasattr(self, "_make_info"):
			del self._make_info

	def _mountall(self):
		self.log.debug("Mounting environment")
		for cmd, mountpoint in self.mountpoints:
			cmd = "%s %s" % (cmd, self.chrootPath(mountpoint))
			chroot.do(cmd, shell=True)

	def _umountall(self):
		self.log.debug("Umounting environment")
		for cmd, mountpoint in self.mountpoints:
			cmd = "umount -n %s" % self.chrootPath(mountpoint)
			chroot.do(cmd, raiseExc=0, shell=True)

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

	def do(self, command, shell=True, personality=None, logger=None, *args, **kwargs):
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
				personality = self.distro.personality

			# Make every shell to a login shell because we set a lot of
			# environment things there.
			if shell:
				command = ["bash", "--login", "-c", command]

			self._mountall()

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

		finally:
			self._umountall()

		return ret

	def make(self, *args, **kwargs):
		if isinstance(self.pkg, packages.Makefile):
			filename = os.path.basename(self.pkg.filename)
		elif isinstance(self.pkg, packages.SourcePackage):
			filename = "%s.%s" % (self.pkg.name, MAKEFILE_EXTENSION)

		return self.do("make -f /build/%s %s" % (filename, " ".join(args)),
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

		self._packages = []
		for pkg in pkgs:
			pkg = packages.VirtualPackage(self.pakfire, pkg)
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
			self.make("build", logger=self.log)

		except Error:
			raise BuildError, "The build command failed."

		for pkg in reversed(self.packages):
			packager = packages.BinaryPackager(self.pakfire, pkg, self)
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
