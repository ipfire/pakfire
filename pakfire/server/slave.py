#!/usr/bin/python

import logging
import os
import socket
import xmlrpclib

import pakfire.downloader
import pakfire.packages

from pakfire.errors import *

class Slave(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

		server = self.pakfire.config._slave.get("server")

		logging.info("Establishing RPC connection to: %s" % server)

		self.conn = xmlrpclib.Server(server)

	@property
	def hostname(self):
		"""
			Return the host's name.
		"""
		return socket.gethostname()

	def keepalive(self):
		"""
			Send the server a keep-alive to say that we are still there.
		"""
		hostname = self.hostname
		l1, l5, l15 = os.getloadavg()

		logging.info("Sending the server a keepalive: %s" % hostname)

		# Get all supported architectures and send them to the server.
		arches = [a for a in self.pakfire.supported_arches]
		arches.sort()

		self.conn.keepalive(hostname, l5, arches)

	def update_build_status(self, build_id, status, message=""):
		self.conn.update_build_state(build_id, status, message)

	def build_job(self):
		build = self.conn.build_job(self.hostname)

		# If the server has got no job for us, we end right here.
		if not build:
			return

		build_id = build["id"]
		filename = build["source"]

		# Get a package grabber and add mirror download capabilities to it.
		grabber = pakfire.downloader.PackageDownloader()

		# Temporary path to store the source.
		tempfile = os.path.join(self.pakfire.tempdir, os.path.basename(filename))

		# Download the source.
		grabber.urlgrab(filename, filename=tempfile)

		# Read the package file.
		pkg = pakfire.packages.SourcePackage(self.pakfire,
			self.pakfire.repos.dummy, tempfile)

		try:
			self.update_build_status(build_id, "running")

			self.pakfire.build(pkg, build_id=build_id)

		except DependencyError, e:
			self.update_build_status(build_id, "dependency_error", e)

		except:
			self.update_build_status(build_id, "failed")

		self.update_build_status(build_id, "finished")

