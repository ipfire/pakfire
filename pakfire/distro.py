#!/usr/bin/python

import logging
import os
import re

from errors import ConfigError
from repository import Repositories

class Distribution(object):
	def __init__(self, pakfire, distro_config=None):
		self.pakfire = pakfire

		self._data = {
			"arch" : self.config.host_arch,
			"name" : "unknown",
			"slogan" : "---",
			"vendor" : "unknown",
			"version" : "0.0",
		}

		# Inherit configuration from Pakfire configuration.
		self.update(self.pakfire.config._distro)

		# Update my configuration from the constructor.
		self.update(distro_config)

		# Dump all data
		self.dump()

	@property
	def config(self):
		return self.pakfire.config

	def dump(self):
		logging.debug("Distribution configuration:")

		attrs = ("name", "version", "release", "sname", "dist", "vendor",
			"arch", "machine",)

		for attr in attrs:
			logging.debug(" %s : %s" % (attr, getattr(self, attr)))

	def update(self, config):
		if not config:
			return

		# Exceptional handling for arch.
		if config.has_key("arch"):
			self.arch = config["arch"]
			del config["arch"]

		self._data.update(config)

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
		return self._data.get("arch") or self.config.host_arch
	
	def set_arch(self, arch):
		# XXX check if we are allowed to set this arch
		if not arch:
			return

		self._data["arch"] = arch

	arch = property(get_arch, set_arch)

	@property
	def dist(self):
		return self.sname[:2] + self.release

	@property
	def machine(self):
		vendor = self.vendor.split()[0]

		return "%s-%s-linux-gnu" % (self.arch, vendor.lower())

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
			"DISTRO_SLOGAN"  : self.slogan,
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

		if self.arch == self.config.host_arch:
			return None

		arch2personality = {
			"x86_64" : "linux64",
			"i686"   : "linux32",
			"i586"   : "linux32",
			"i486"   : "linux32",
		}

		return arch2personality[self.arch]
