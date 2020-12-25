#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2016 Pakfire development team                                 #
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

import logging

log = logging.getLogger("pakfire.arch")
log.propagate = 1

class Arch(object):
	def __init__(self, name):
		assert name

		self.name = name

	def __str__(self):
		return self.name

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __eq__(self, other):
		return self.name == other.name

	@property
	def platform(self):
		"""
			Returns the "class" this architecture belongs to.
		"""
		if self.name.startswith("arm") or self.name == "aarch64":
			return "arm"

		if self.name in ("i686", "x86_64"):
			return "x86"

		return "unknown"

	def get_machine(self, vendor=None):
		if vendor is None:
			vendor = "unknown"

		# Make vendor lowercase
		vendor = vendor.lower()
		assert vendor

		s = "%s-%s-linux-gnu" % (self.name, vendor)

		if self.name.startswith("arm"):
			s += "eabi"

		return s

	def get_buildtarget(self, vendor=None):
		machine = self.get_machine(vendor)

		# Cut off last segment of machine.
		return machine.replace("-gnu", "")

	@property
	def compatible_arches(self):
		"""
			Returns a list of all architectures that are
			compatible (i.e. can be emulated)
		"""
		x = {
			# Host arch : Can build these arches.
			# x86
			"x86_64"    : ["x86_64", "i686",],
			"i686"      : ["i686",],

			# ARM
			"armv5tel"  : ["armv5tel",],
			"armv5tejl" : ["armv5tel",],
			"armv6l"    : ["armv5tel",],
			"armv7l"    : ["armv7hl", "armv5tel",],
			"armv7hl"   : ["armv7hl", "armv5tel",],

			"aarch64"   : ["aarch64",],
		}

		try:
			return (Arch(a) for a in x[self.name])
		except KeyError:
			return []

	def is_compatible_with(self, arch):
		"""
			Returns True if the given architecture is compatible
			with this architecture.
		"""
		return arch in self.compatible_arches

	@property
	def personality(self):
		"""
			Return the personality of the target system.

			If host and target system are of the same architecture, we return
			None to skip the setting of the personality in the build chroot.
		"""
		arch2personality = {
			"x86_64" : "linux64",
			"i686"   : "linux32",
			"i586"   : "linux32",
			"i486"   : "linux32",
		}

		try:
			personality = arch2personality[self.name]
		except KeyError:
			personality = None

		return personality
