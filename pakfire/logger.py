#!/usr/bin/python

import logging

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
