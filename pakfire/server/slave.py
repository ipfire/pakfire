#!/usr/bin/python

import logging
import os
import socket
import tempfile
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

		print build

		build_id = build["id"]
		filename = build["name"]
		download = build["download"]
		hash1    = build["hash1"]

		# Create a temporary file and a directory for the resulting files.
		tmpdir = tempfile.mkdtemp()
		tmpfile = os.path.join(tmpdir, filename)

		# Get a package grabber and add mirror download capabilities to it.
		grabber = pakfire.downloader.PackageDownloader()

		try:
			# Download the source.
			grabber.urlgrab(download, filename=tmpfile)

			# Check if the download checksum matches.
			if pakfire.util.calc_hash1(tmpfile) == hash1:
				print "Checksum matches: %s" % hash1
			else:
				raise DownloadError, "Download was corrupted"

			# Update the build status on the server.
			self.update_build_status(build_id, "running")

			# Run the build.
			pakfire.api.build(tmpfile, build_id=build_id,
				resultdirs=[tmpdir,])

			self.update_build_status(build_id, "uploading")

			for dir, subdirs, files in os.walk(tmpdir):
				for file in files:
					file = os.path.join(dir, file)
					if file == tmpfile:
						continue

					pkg = pakfire.packages.open(self.pakfire, None, file)

					self.upload_package_file(build["source_id"], build["pkg_id"], pkg)

		except DependencyError, e:
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "dependency_error", message)

		except Exception, e:
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "failed", message)
			raise

		else:
			self.update_build_status(build_id, "finished")

		finally:
			# Cleanup the files we created.
			pakfire.util.rm(tmpdir)
