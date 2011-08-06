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

from i18n import _

class Error(Exception):
	exit_code = 1

	message = _("An unhandled error occured.")


class ActionError(Error):
	pass

class BuildAbortedException(Error):
	pass

class BuildError(Error):
	pass

class BuildRootLocked(Error):
	pass

class ConfigError(Error):
	pass

class DependencyError(Error):
	exit_code = 4

	message = _("One or more dependencies could not been resolved.")

class DownloadError(Error):
	pass

class FileError(Error):
	pass

class FileNotFoundError(Error):
	pass

class NotAnIPFireSystemError(Error):
	pass

class OfflineModeError(Error):
	message = _("The requested action cannot be done on offline mode.\n"
		"Please connect your system to the network, remove --offline from the"
		" command line and try again.")

class PakfireError(Error):
	pass

