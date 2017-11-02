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

class UI(object):
	def __init__(self):
		pass

	def is_interactive(self):
		"""
			Returns True if a user can interact with the interface.
		"""
		raise NotImplementedError

	def alert(self, msg):
		"""
			Prints an important message to the user.
		"""
		raise NotImplementedError

	def message(self, msg, level=None):
		raise NotImplementedError

	def confirm(self, message=None):
		raise NotImplementedError
