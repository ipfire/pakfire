#!/usr/bin/python

import logging
import os
import socket
import xmlrpclib

class Slave(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

		server = self.pakfire.config._slave.get("server")

		logging.info("Establishing RPC connection to: %s" % server)

		self.conn = xmlrpclib.Server(server)

	def keepalive(self):
		"""
			Send the server a keep-alive to say that we are still there.
		"""
		hostname = socket.gethostname()
		l1, l5, l15 = os.getloadavg()

		logging.info("Sending the server a keepalive: %s" % hostname)

		self.conn.keepalive(hostname, l5)

