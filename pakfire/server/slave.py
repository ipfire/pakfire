#!/usr/bin/python

import logging
import os
import socket
import xmlrpclib

import pakfire.api
import pakfire.base
import pakfire.downloader
import pakfire.packages
import pakfire.util

from pakfire.constants import *

from base import MasterSlave

class Slave(MasterSlave):
	def __init__(self, **pakfire_args):
		self.pakfire = pakfire.base.Pakfire(**pakfire_args)

		server = self.pakfire.config._slave.get("server")

		logging.info("Establishing RPC connection to: %s" % server)

		self.conn = xmlrpclib.Server(server)

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
		filename = build["name"]
		data     = build["data"].data
		hash1    = build["hash1"]

		# XXX need to find a better temp dir.
		tempfile = os.path.join("/var/tmp", filename)
		resultdir = os.path.join("/var/tmp", build_id)

		try:
			# Check if the download checksum matches.
			if pakfire.util.calc_hash1(data=data) == hash1:
				print "Checksum matches: %s" % hash1
			else:
				raise DownloadError, "Download was corrupted"

			# Save the data to a temporary directory.
			f = open(tempfile, "wb")
			f.write(data)
			f.close()

			# Update the build status on the server.
			self.update_build_status(build_id, "running")

			# Run the build.
			pakfire.api.build(tempfile, build_id=build_id,
				resultdirs=[resultdir,])

			self.update_build_status(build_id, "uploading")

			for dir, subdirs, files in os.walk(resultdir):
				for file in files:
					file = os.path.join(dir, file)

					pkg = pakfire.packages.open(self.pakfire, None, file)

					self.upload_package_file(build["source_id"], build["pkg_id"], pkg)

		except DependencyError, e:
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "dependency_error", message)

		except Exception, e:
			raise
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "failed", message)
			raise

		else:
			self.update_build_status(build_id, "finished")

		finally:
			#pakfire.util.rm(tempfile)
			pass
