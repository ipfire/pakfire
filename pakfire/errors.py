#!/usr/bin/python

class Error(Exception):
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

class PakfireError(Error):
	pass

