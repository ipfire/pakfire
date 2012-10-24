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

class commandTimeoutExpired(Exception):
	pass # XXX cannot be as is

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

class CompressionError(Error):
	message = _("Could not compress/decompress data.")


class ConfigError(Error):
	pass

class DatabaseError(Error):
	pass

class DependencyError(Error):
	exit_code = 4

	message = _("One or more dependencies could not been resolved.")

class DownloadError(Error):
	message = _("An error occured when pakfire tried to download files.")


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

class PackageFormatUnsupportedError(Error):
	pass

class PakfireError(Error):
	pass


class PakfireContainerError(Error):
	message = _("Running pakfire-build in a pakfire container?")


class ShellEnvironmentError(Error):
	pass


class SignatureError(Error):
	pass


class TransactionCheckError(Error):
	message = _("Transaction test was not successful")


class XMLRPCError(Error):
	message = _("Generic XMLRPC error.")


class XMLRPCForbiddenError(XMLRPCError):
	message = _("You are forbidden to perform this action. Maybe you need to check your credentials.")


class XMLRPCInternalServerError(XMLRPCError):
	message = _("A request could not be fulfilled by the server.")


class XMLRPCNotFoundError(XMLRPCError):
	message = _("Could not find the requested URL.")


class XMLRPCTransportError(XMLRPCError):
	message = _("An unforseable problem on the XML-RPC transport connection occured.")
