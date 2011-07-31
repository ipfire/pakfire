#!/usr/bin/python

import tarfile

from binary import BinaryPackage
from file import InnerTarFile
from installed import DatabasePackage, InstalledPackage
from solv import SolvPackage
from source import SourcePackage
from virtual import VirtualPackage

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
