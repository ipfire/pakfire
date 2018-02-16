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

import logging
import time

class PakfireLogHandler(logging.Handler):
	LOG_EMERG     = 0       #  system is unusable
	LOG_ALERT     = 1       #  action must be taken immediately
	LOG_CRIT      = 2       #  critical conditions
	LOG_ERR       = 3       #  error conditions
	LOG_WARNING   = 4       #  warning conditions
	LOG_NOTICE    = 5       #  normal but significant condition
	LOG_INFO      = 6       #  informational
	LOG_DEBUG     = 7       #  debug-level messages

	priority_map = {
		"DEBUG"    : LOG_DEBUG,
		"INFO"     : LOG_INFO,
		"WARNING"  : LOG_WARNING,
		"ERROR"    : LOG_ERR,
		"CRITICAL" : LOG_CRIT,
	}

	def __init__(self, pakfire):
		logging.Handler.__init__(self)

		self.pakfire = pakfire

	def emit(self, record):
		line = self.format(record)
		prio = self._get_priority(record.levelname)

		self.pakfire._log(prio, line, filename=record.pathname,
			lineno=record.lineno, function=record.funcName)

	def _get_priority(self, level):
		return self.priority_map.get(level, self.LOG_WARNING)


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
