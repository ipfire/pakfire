#!/usr/bin/python

import logging
import os
import re

from errors import ConfigError

class Distribution(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

		self._data = {
			"arch" : self.host_arch,
			"name" : "unknown",
			"slogan" : "---",
			"vendor" : "unknown",
			"version" : "0.0",
		}

		if not self.pakfire.config._distro:
			raise ConfigError, "No distribution data was provided in the configuration"

		# Import settings from Config()
		self._data.update(self.pakfire.config._distro)

		# Dump all data
		self.dump()

	def dump(self):
		logging.debug("Distribution configuration:")

		attrs = ("name", "version", "release", "sname", "dist", "vendor", "machine",)

		for attr in attrs:
			logging.debug(" %s : %s" % (attr, getattr(self, attr)))

	@property
	def name(self):
		return self._data.get("name")

	@property
	def version(self):
		return self._data.get("version")

	@property
	def release(self):
		m = re.match(r"^([0-9]+)\..*", self.version)

		return m.group(1)

	@property
	def sname(self):
		return self.name.strip().lower()

	@property
	def slogan(self):
		return self._data.get("slogan")

	@property
	def vendor(self):
		return self._data.get("vendor")

	def get_arch(self):
		return self._data.get("arch")
	
	def set_arch(self, arch):
		# XXX check if we are allowed to set this arch
		self._data.set("arch", arch)

	arch = property(get_arch, set_arch)

	@property
	def dist(self):
		return self.sname[:2] + self.release

	@property
	def machine(self):
		return "%s-%s-linux-gnu" % (self.arch, self.vendor)

	@property
	def host_arch(self):
		"""
			Return the architecture of the host we are running on.
		"""
		return os.uname()[4]

	@property
	def supported_arches(self):
		host_arches = {
			"i686" : [ "i686", "x86_64", ],
			"i586" : [ "i586", "i686", "x86_64", ],
			"i486" : [ "i486", "i586", "i686", "x86_64", ],
		}

		for host, can_be_built in host_arches.items():
			if self.host_arch in can_be_built:
				yield host

	def host_supports_arch(self, arch):
		"""
			Check if this host can build for the target architecture "arch".
		"""
		return arch in self.supported_arches

	@property
	def environ(self):
		"""
			An attribute that adds some environment variables to the
			chroot environment.
		"""
		env = {
			"DISTRO_NAME"    : self.name,
			"DISTRO_SNAME"   : self.sname,
			"DISTRO_VERSION" : self.version,
			"DISTRO_RELEASE" : self.release,
			"DISTRO_DISTTAG" : self.dist,
			"DISTRO_ARCH"    : self.arch,
			"DISTRO_MACHINE" : self.machine,
			"DISTRO_VENDOR"  : self.vendor,
		}

		return env

	@property
	def info(self):
		info = {}

		for k, v in self.environ.items():
			info[k.lower()] = v

		return info

	@property
	def personality(self):
		"""
			Return the personality of the target system.

			If host and target system are of the same architecture, we return
			None to skip the setting of the personality in the build chroot.
		"""

		if self.arch == self.host_arch:
			return None

		arch2personality = {
			"x86_64" : "linux64",
			"i686"   : "linux32",
			"i586"   : "linux32",
			"i486"   : "linux32",
		}

		return arch2personality[self.arch]

