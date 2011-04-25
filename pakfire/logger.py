#!/usr/bin/python

import logging
import time

def setup_logging(config):
	"""
		This function initialized the logger that is enabled immediately.
	"""

	l = logging.getLogger()

	if len(l.handlers) > 1:
		logging.debug("Logging was already set up. Don't do this again.")
		return

	# Remove all previous defined handlers.
	for handler in l.handlers:
		l.removeHandler(handler)

	# Set level of logger always to DEBUG.
	l.setLevel(logging.DEBUG)

	# But only log all the debugging stuff on console if
	# we are running in debugging mode.
	handler = logging.StreamHandler()

	if config.get("debug"):
		handler.setLevel(logging.DEBUG)
	else:
		handler.setLevel(logging.INFO)

	l.addHandler(handler)

	# The configuration file always logs all messages.
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
