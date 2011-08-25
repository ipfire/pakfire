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

import tarfile

from binary import BinaryPackage
from file import InnerTarFile
from installed import DatabasePackage, InstalledPackage
from solv import SolvPackage
from source import SourcePackage

from make import Makefile
from packager import BinaryPackager

from pakfire.constants import *

def open(pakfire, repo, filename):
	"""
		Function to open all packages and return the right object.

		Abstractly, this detects if a package is a source package or
		not.
	"""
	# XXX We should make this check much better...

	# Simply check if the given file is a tarfile.
	if tarfile.is_tarfile(filename):
		if filename.endswith(".src.%s" % PACKAGE_EXTENSION):
			return SourcePackage(pakfire, repo, filename)

		return BinaryPackage(pakfire, repo, filename)

	elif filename.endswith(".%s" % MAKEFILE_EXTENSION):
		return Makefile(pakfire, filename)
