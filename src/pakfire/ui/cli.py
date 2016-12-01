#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2014 Pakfire development team                                 #
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

import sys

from . import base
from . import helpers

class CliUI(base.UI):
	def write(self, data):
		print(data)

	def is_interactive(self):
		"""
			Returns True if this is running on an interactive shell.
		"""
		return sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()

	def message(self, msg, level=None):
		"""
			Simply print out the given message.
		"""
		self.write(msg)
