#!/usr/bin/python

class Plugin(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

		self.init()

	def init(self):
		"""
			Initialization function that it to be overwritten
			by the actual plugin.
		"""
		pass
