#!/usr/bin/python

import os
import sys

# Try to load the _pakfire module.
import pakfire

# Check that we didn't load the system's version.
topdir = os.environ.get("topdir")

if not pakfire.__file__.startswith(topdir):
	print "Wrong module loaded..."
	sys.exit(1)
