#!/usr/bin/python

from __future__ import division

import os
import socket
import urlparse
import xmlrpclib

import pakfire.util
import pakfire.packages as packages
from pakfire.system import system

# Local modules.
import transport

from pakfire.constants import *
from pakfire.i18n import _

import logging
log = logging.getLogger("pakfire.client")

class PakfireClient(object):
	type = None

	def __init__(self, server, username, password):
		self.url = self._join_url(server, username, password)

		# Create a secure XMLRPC connection to the server.
		self.conn = transport.Connection(self.url)

	def _join_url(self, server, username, password):
		"""
			Construct a right URL out of the given
			server, username and password.

			Basicly this just adds the credentials
			to the URL.
		"""
		assert self.type

		# Parse the given URL.
		url = urlparse.urlparse(server)
		assert url.scheme in ("http", "https")

		# Build new URL.
		ret = "%s://" % url.scheme

		# Add credentials if provided.
		if username and password:
			ret += "%s:%s@" % (username, password)

		# Add host and path components.
		ret += "/".join((url.netloc, self.type))

		return ret

	### Misc. actions

	def noop(self):
		"""
			No operation. Just to check if the connection is
			working. Returns a random number.
		"""
		return self.conn.noop()

	def get_my_address(self):
		"""
			Get my own address (as seen by the hub).
		"""
		return self.conn.get_my_address()

	def get_hub_status(self):
		"""
			Get some status information about the hub.
		"""
		return self.conn.get_hub_status()


class BuildMixin(object):
	### Build actions

	def build_create(self, filename, arches=None, distro=None):
		"""
			Create a new build on the hub.
		"""

		# Upload the source file to the server.
		upload_id = self._upload_file(filename)

		# Then create the build.
		build = self.conn.build_create(upload_id, distro, arches)

		print build

	def _upload_file(self, filename):
		# Get the hash of the file.
		hash = pakfire.util.calc_hash1(filename)

		# Get the size of the file.
		size = os.path.getsize(filename)

		# Get an upload ID from the server.
		upload_id = self.conn.upload_create(os.path.basename(filename),
			size, hash)

		# Make a nice progressbar.
		pb = pakfire.util.make_progress(os.path.basename(filename), size, speed=True, eta=True)

		try:
			# Calculate the number of chunks.
			chunks = (size // CHUNK_SIZE) + 1
			transferred = 0

			# Cut the file in pieces and upload them one after another.
			with open(filename) as f:
				chunk = 0
				while True:
					data = f.read(CHUNK_SIZE)
					if not data:
						break

					chunk += 1
					if pb:
						transferred += len(data)
						pb.update(transferred)

					data = xmlrpclib.Binary(data)
					self.conn.upload_chunk(upload_id, data)

			# Tell the server, that we finished the upload.
			ret = self.conn.upload_finished(upload_id)

		except:
			# If anything goes wrong, try to delete the upload and raise
			# the exception.
			self.conn.upload_remove(upload_id)

			raise

		finally:
			if pb:
				pb.finish()

		# If the server sends false, something happened with the upload that
		# could not be recovered.
		if not ret:
			logging.error("Upload of %s was not successful." % filename)
			raise Exception, "Upload failed."

		return upload_id


class PakfireUserClient(BuildMixin, PakfireClient):
	type = "user"

	def check_auth(self):
		"""
			Check if the user was successfully authenticated.
		"""
		return self.conn.check_auth()

	def get_user_profile(self):
		"""
			Get information about the user profile.
		"""
		return self.conn.get_user_profile()

	def get_builds(self, type=None, limit=10, offset=0):
		return self.conn.get_builds(type=type, limit=limit, offset=offset)

	def get_build(self, build_id):
		return self.conn.get_build(build_id)

	def get_builder(self, builder_id):
		return self.conn.get_builder(builder_id)

	def get_job(self, job_id):
		return self.conn.get_job(job_id)

	def get_latest_jobs(self):
		return self.conn.get_latest_jobs()

	def get_active_jobs(self):
		return self.conn.get_active_jobs()


class PakfireBuilderClient(BuildMixin, PakfireClient):
	type = "builder"

	def send_keepalive(self, overload=None, free_space=None):
		"""
			Sends a little keepalive to the server and
			updates the hardware information if the server
			requests it.
		"""
		log.debug("Sending keepalive to the hub.")

		# Collect the current loadavg and send it to the hub.
		loadavg = ", ".join(("%.2f" % round(l, 2) for l in os.getloadavg()))

		needs_update = self.conn.send_keepalive(loadavg, overload, free_space)

		if needs_update:
			log.debug("The hub is requesting an update.")
			self.send_update()

	def send_update(self):
		log.info("Sending host information update to hub...")

		self.conn.send_update(
			# Supported architectures.
			system.supported_arches,

			# CPU information.
			system.cpu_model,
			system.cpu_count,

			# Amount of memory in bytes.
			system.memory / 1024,

			# Send the currently running version of Pakfire.
			PAKFIRE_VERSION,
		)
