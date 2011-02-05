#!/usr/bin/python

import logging

class Plugins(object):
	allowed_methods = ["init",]

	def __init__(self, pakfire):
		self.pakfire = pakfire

		self.__plugins = []

	def run(self, method):
		if not method in self.allowed_methods:
			raise Exception, "Unallowed method called '%s'" % method

		logging.debug("Running plugin method '%s'" % method)

