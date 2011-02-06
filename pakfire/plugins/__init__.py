#!/usr/bin/python

import logging

class Plugins(object):
	allowed_methods = ["init",]

	def __init__(self, pakfire):
		self.pakfire = pakfire

		self.__plugins = []

	def register_plugin(self, plugin):
		# Create instance of plugin
		plugin = plugin(self.pakfire)

		self.__plugins.append(plugin)

	def run(self, method, *args, **kwargs):
		if not method in self.allowed_methods:
			raise Exception, "Unallowed method called '%s'" % method

		logging.debug("Running plugin method '%s'" % method)

		for plugin in self.__plugins:
			func = getattr(plugin, method, None)
			if not func:
				continue

			func(*args, **kwargs)
