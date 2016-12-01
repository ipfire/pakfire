#!/usr/bin/python3
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

import time

import logging
import logging.handlers

def setup_logging(debug=False):
	"""
		This function initialized the logger that is enabled immediately
	"""
	l = logging.getLogger("pakfire")
	l.propagate = 0

	# Set level of logger always to DEBUG.
	l.setLevel(logging.DEBUG)

	# Remove all previous defined handlers.
	l.handlers = []

	# Log to syslog
	handler = logging.handlers.SysLogHandler("/dev/log")
	l.addHandler(handler)

	# Formatter
	f = logging.Formatter("%(name)s: %(message)s")
	handler.setFormatter(f)

	# Configure debugging
	if not debug:
		handler.setLevel(logging.INFO)

	return l

class BuildFormatter(logging.Formatter):
	def __init__(self):
		self._fmt = "[%(asctime)s] %(message)s"
		self.datefmt = None

		self.starttime = time.time()

	def converter(self, recordtime):
		"""
			This returns a timestamp relatively to the time when we started
			the build.
		"""
		recordtime -= self.starttime

		return time.gmtime(recordtime)

	def formatTime(self, record, datefmt=None):
		ct = self.converter(record.created)
		t = time.strftime("%H:%M:%S", ct)
		s = "%s,%03d" % (t, record.msecs)
		return s
