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
from master import Source

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

		job_types = {
			"binary" : self.build_binary_job,
			"source" : self.build_source_job,
		}

		build_id   = build["id"]
		build_type = build["type"]

		try:
			func = job_types[build_type]
		except KeyError:
			raise Exception, "Build type not supported: %s" % type

		# Call the function that processes the build and try to catch general
		# exceptions and report them to the server.
		# If everything goes okay, we tell this the server, too.
		try:
			func(build_id, build)

		except Exception, e:
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "failed", message)
			raise

		else:
			self.update_build_status(build_id, "finished")

	def build_binary_job(self, build_id, build):
		arch     = build["arch"]
		filename = build["name"]
		download = build["download"]
		hash1    = build["hash1"]

		# Create a temporary file and a directory for the resulting files.
		tmpdir = tempfile.mkdtemp()
		tmpfile = os.path.join(tmpdir, filename)
		logfile = os.path.join(tmpdir, "build.log")

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
				resultdirs=[tmpdir,], logfile=logfile)

			self.update_build_status(build_id, "uploading")

			for dir, subdirs, files in os.walk(tmpdir):
				for file in files:
					file = os.path.join(dir, file)
					if file in (logfile, tmpfile,):
						continue

					pkg = pakfire.packages.open(self.pakfire, None, file)

					self.upload_package_file(build["source_id"], build["pkg_id"], pkg)

		except DependencyError, e:
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "dependency_error", message)

		finally:
			# Upload the logfile in any case and if it exists.
			if os.path.exists(logfile):
				self.upload_log_file(build_id, logfile)

			# Cleanup the files we created.
			pakfire.util.rm(tmpdir)

	def build_source_job(self, build_id, build):
		# Update the build status on the server.
		self.update_build_status(build_id, "running")

		source = Source(self, **build["source"])

		source.update_revision((build["revision"], False), build_id=build_id)
