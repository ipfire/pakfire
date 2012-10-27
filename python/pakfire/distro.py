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

import os
import re

import logging
log = logging.getLogger("pakfire")

from system import system

class Distribution(object):
	def __init__(self,  data=None):
		self._data = {}

		if data:
			self.update(data)
		else:
			# Read /etc/os-release if it does exist.
			self.read_osrelease()

		# Dump all data
		self.dump()

	def read_osrelease(self):
		filename = "/etc/os-release"

		if not os.path.exists(filename):
			return

		keymap = {
			"NAME"       : "name",
			"VERSION_ID" : "release",
		}

		data = {}

		f = open(filename)
		for line in f.readlines():
			m = re.match(r"^(.*)=(.*)$", line)
			if m:
				k, v = m.groups()

				v = v.replace("\"", "")
				v = v.strip()

				try:
					k = keymap[k]
				except KeyError:
					continue

				data[k] = v
		f.close()

		self.update(data)

	def dump(self):
		log.debug("Distribution configuration:")

		attrs = ("name", "release", "sname", "dist", "vendor", "contact",
			"arch", "machine", "buildtarget", "source_dl",)

		for attr in attrs:
			log.debug(" %s : %s" % (attr, getattr(self, attr)))

	def get_config(self):
		lines = [
			"[distro]",
			"name = %s" % self.name,
			"release = %s" % self.release,
			"slogan = %s" % self.slogan,
			"",
			"vendor = %s" % self.vendor,
			"contact = %s" % self.contact,
		]

		return "\n".join(lines)

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
		return self._data.get("name", "unknown")

	@property
	def release(self):
		return self._data.get("release", "0")

	@property
	def sname(self):
		return self.name.strip().lower()

	@property
	def slogan(self):
		return self._data.get("slogan", "N/A")

	@property
	def vendor(self):
		vendor = self._data.get("vendor")
		if vendor is None:
			vendor = "%s Project" % self.name

		return vendor

	@property
	def contact(self):
		return self._data.get("contact", "N/A")

	def get_arch(self):
		arch = self._data.get("arch", None) or system.arch

		# We can not set up a build environment for noarch.
		if arch == "noarch":
			arch = system.arch

		return arch
	
	def set_arch(self, arch):
		# XXX check if we are allowed to set this arch
		if not arch:
			return

		self._data["arch"] = arch

	arch = property(get_arch, set_arch)

	@property
	def platform(self):
		"""
			Returns the "class" this architecture belongs to.
		"""
		if self.arch.startswith("arm"):
			return "arm"

		if self.arch in ("i686", "x86_64"):
			return "x86"

		return "unknown"

	@property
	def dist(self):
		return self.sname[:2] + self.release

	@property
	def machine(self):
		vendor = self.vendor.split()[0]

		s = "%s-%s-linux-gnu" % (self.arch, vendor.lower())

		if self.arch.startswith("arm"):
			s += "eabi"

		return s

	@property
	def buildtarget(self):
		# Cut off last segment of machine.
		return self.machine.replace("-gnu", "")

	@property
	def source_dl(self):
		return self._data.get("source_dl", None)

	@property
	def environ(self):
		"""
			An attribute that adds some environment variables to the
			chroot environment.
		"""
		env = {
			"DISTRO_NAME"         : self.name,
			"DISTRO_SNAME"        : self.sname,
			"DISTRO_RELEASE"      : self.release,
			"DISTRO_DISTTAG"      : self.dist,
			"DISTRO_ARCH"         : self.arch,
			"DISTRO_MACHINE"      : self.machine,
			"DISTRO_PLATFORM"     : self.platform,
			"DISTRO_BUILDTARGET"  : self.buildtarget,
			"DISTRO_VENDOR"       : self.vendor,
			"DISTRO_CONTACT"      : self.contact,
			"DISTRO_SLOGAN"       : self.slogan,
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

		if self.arch == system.native_arch:
			return None

		arch2personality = {
			"x86_64" : "linux64",
			"i686"   : "linux32",
			"i586"   : "linux32",
			"i486"   : "linux32",
		}

		try:
			personality = arch2personality[self.arch]
		except KeyError:
			personality = None

		return personality
