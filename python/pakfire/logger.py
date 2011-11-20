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

import time

import logging
log = logging.getLogger("pakfire")

def setup_logging(config=None):
	"""
		This function initialized the logger that is enabled immediately.
	"""
	l = logging.getLogger("pakfire")
	l.propagate = 0

	if len(l.handlers) > 1:
		l.debug("Logging was already set up. Don't do this again.")
		return

	# Remove all previous defined handlers.
	for handler in l.handlers:
		l.removeHandler(handler)

	# Set level of logger always to DEBUG.
	l.setLevel(logging.DEBUG)

	# But only log all the debugging stuff on console if
	# we are running in debugging mode.
	handler = logging.StreamHandler()

	if config and config.get("debug"):
		handler.setLevel(logging.DEBUG)
	else:
		handler.setLevel(logging.INFO)

	l.addHandler(handler)

	# The configuration file always logs all messages.
	if config:
		handler = logging.FileHandler(config.get("logfile"))
		handler.setLevel(logging.DEBUG)
		l.addHandler(handler)


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
