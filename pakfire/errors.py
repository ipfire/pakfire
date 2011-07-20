#!/usr/bin/python

class Error(Exception):
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
	pass

class DownloadError(Error):
	pass

class FileError(Error):
	pass

class FileNotFoundError(Error):
	pass

class NotAnIPFireSystemError(Error):
	pass

class PakfireError(Error):
	pass

