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

"""
	The translation process of all strings is done in here.
"""

import  gettext

"""
	A function that returnes the same string.
"""
N_ = lambda x: x

def _(singular, plural=None, n=None):
	"""
		A function that returnes the translation of a string if available.

		The language is taken from the system environment.
	"""
	if not plural is None:
		assert n is not None
		return gettext.dngettext("pakfire", singular, plural, n)

	return gettext.dgettext("pakfire", singular)

def list(parts):
	"""
		Returns a comma-separated list for the given list of parts.

		The format is, e.g., "A, B and C", "A and B" or just "A" for lists
		of size 1.
	"""
	if len(parts) == 0: return ""
	if len(parts) == 1: return parts[0]
	return _("%(commas)s and %(last)s") % {
		"commas": u", ".join(parts[:-1]),
		"last": parts[len(parts) - 1],
	}
