#!/usr/bin/python

import fcntl
import grp
import logging
import os
import re
import shutil
import stat
import time

import depsolve
import packages
import transaction
import util

from constants import *
from errors import BuildRootLocked


class Builder(object):
	# The version of the kernel this machine is running.
	kernel_version = os.uname()[2]

	def __init__(self, pakfire, pkg):
		self.pakfire = pakfire
		self.pkg = pkg

		self.settings = {
			"enable_loop_devices" : True,
		}

		self.buildroot = "/buildroot"

		# Lock the buildroot
		self._lock = None
		self.lock()

		# Initialize the environment
		self.prepare()

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

	def extract(self, requires=[], build_deps=True):
		"""
			Gets a dependency set and extracts all packages
			to the environment.
		"""
		ds = depsolve.DependencySet(self.pakfire)
		for p in BUILD_PACKAGES + requires:
			ds.add_requires(p)
		ds.resolve()

		# Get build dependencies from source package.
		if isinstance(self.pkg, packages.SourcePackage):
			for req in self.pkg.requires:
				ds.add_requires(req)

		ts = transaction.TransactionSet(self.pakfire, ds)
		ts.dump()
		ts.run()

		# Copy the makefile and load source tarballs.
		if isinstance(self.pkg, packages.Makefile):
			self.pkg.extract(self)

		# If we have a makefile, we can only get the build dependencies
		# after we have extracted all the rest.
		if build_deps and isinstance(self.pkg, packages.Makefile):
			requires = self.make_requires()
			if not requires:
				return

			ds = depsolve.DependencySet(self.pakfire)
			for r in requires:
				ds.add_requires(r)
			ds.resolve()

			ts = transaction.TransactionSet(self.pakfire, ds)
			ts.dump()
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
		for dir in dirs:
			dir = self.chrootPath(dir)
			if not os.path.exists(dir):
				os.makedirs(dir)

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

	def cleanup(self):
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

		return ret

	@property
	def environ(self):
		env = {
			"BUILDROOT" : self.buildroot,
		}

		# Inherit environment from distro
		env.update(self.pakfire.distro.environ)

		# XXX what do we need else?

		return env

	def do(self, command, shell=True, personality=None, *args, **kwargs):
		ret = None
		try:
			# Environment variables
			env = self.environ

			if kwargs.has_key("env"):
				env.update(kwargs.pop("env"))

			# Update personality it none was set
			if not personality:
				personality = self.pakfire.distro.personality

			self._mountall()

			if not kwargs.has_key("chrootPath"):
				kwargs["chrootPath"] = self.chrootPath()

			ret = util.do(
				command,
				personality=personality,
				shell=shell,
				env=env,
				logger=self.log,
				*args,
				**kwargs
			)

		finally:
			self._umountall()

		return ret

	def make(self, *args, **kwargs):
		command = ["bash", "--login", "-c",]
		command.append("make -f /build/%s %s" % \
			(os.path.basename(self.pkg.filename), " ".join(args)))

		return self.do(command,	shell=False, **kwargs)

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
			pkg = packages.VirtualPackage(pkg)
			self._packages.append(pkg)

		return self._packages

	def make_requires(self):
		return self.make_info.get("PKG_BUILD_DEPS", "").split()

	def make_sources(self):
		return self.make_info.get("PKG_FILES", "").split()

	def build(self):
		self.make("build")

		for pkg in reversed(self.packages):
			packager = packages.Packager(self.pakfire, pkg, self)
			packager()

	def dist(self):
		self.pkg.dist(self)

	def shell(self, args=[]):
		# XXX need to add linux32 or linux64 to the command line
		# XXX need to set CFLAGS here
		command = "chroot %s /usr/bin/chroot-shell %s" % \
			(self.chrootPath(), " ".join(args))

		for key, val in self.environ.items():
			command = "%s=\"%s\" " % (key, val) + command

		# Add personality if we require one
		if self.pakfire.distro.personality:
			command = "%s %s" % (self.pakfire.disto.personality, command)

		# Empty the environment
		#command = "env -i - %s" % command

		logging.debug("Shell command: %s" % command)

		try:
			self._mountall()

			shell = os.system(command)
			return os.WEXITSTATUS(shell)

		finally:
			self._umountall()
