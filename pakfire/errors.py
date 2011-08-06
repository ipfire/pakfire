#!/usr/bin/python

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

