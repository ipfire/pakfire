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

	# Remove all previous defined handlers
	for handler in l.handlers:
		l.removeHandler(handler)

	if config.get("debug"):
		l.setLevel(logging.DEBUG)

	handler = logging.StreamHandler()
	l.addHandler(handler)

	handler = logging.FileHandler(config.get("logfile"))
	handler.setLevel(logging.DEBUG)
	l.addHandler(handler)
