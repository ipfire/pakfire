#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2013 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

from __future__ import division

import base64
import hashlib
import json
import os
import time
import urlgrabber
import urllib
import urlparse

import pakfire.downloader
import pakfire.util

from pakfire.constants import *
from pakfire.i18n import _

import logging
log = logging.getLogger("pakfire.transport")


class PakfireHubTransportUploader(object):
	"""
		Handles the upload of a single file to the hub.
	"""

	def __init__(self, transport, filename):
		self.transport = transport
		self.filename = filename

	def get_upload_id(self):
		"""
			Gets an upload from the pakfire hub.
		"""
		# Calculate the SHA1 sum of the file to upload.
		h = hashlib.new("sha1")
		with open(self.filename, "rb") as f:
			while True:
				buf = f.read(CHUNK_SIZE)
				if not buf:
					break

				h.update(buf)

		data = {
			"filename" : os.path.basename(self.filename),
			"filesize" : os.path.getsize(self.filename),
			"hash"     : h.hexdigest(),
		}

		upload_id = self.transport.get("/uploads/create", data=data)
		log.debug("Got upload id: %s" % upload_id)

		return upload_id

	def send_file(self, upload_id, progress_callback=None):
		"""
			Sends the file content to the server.

			The data is splitted into chunks, which are
			sent one after an other.
		"""
		with open(self.filename, "rb") as f:
			# Initial chunk size.
			chunk_size = CHUNK_SIZE

			# Count the already transmitted bytes.
			transferred = 0

			while True:
				chunk = f.read(chunk_size)
				if not chunk:
					break

				log.debug("Got chunk of %s bytes" % len(chunk))

				# Save the time when we started to send this bit.
				time_started = time.time()

				# Send the chunk to the server.
				self.send_chunk(upload_id, chunk)

				# Save the duration.time after the chunk has been transmitted
				# and adjust chunk size to send one chunk per second.
				duration = time.time() - time_started
				chunk_size = int(chunk_size / duration)

				# Never let chunk_size drop under CHUNK_SIZE:
				if chunk_size < CHUNK_SIZE:
					chunk_size = CHUNK_SIZE

				# Add up the send amount of data.
				transferred += len(chunk)
				if progress_callback:
					progress_callback(transferred)

	def send_chunk(self, upload_id, data):
		"""
			Sends a piece of the file to the server.
		"""
		# Calculate checksum over the chunk data.
		h = hashlib.new("sha512")
		h.update(data)
		chksum = h.hexdigest()

		# Encode data in base64.
		data = base64.b64encode(data)

		# Send chunk data to the server.
		self.transport.post("/uploads/%s/sendchunk" % upload_id,
			data={ "chksum" : chksum, "data" : data })

	def destroy_upload(self, upload_id):
		"""
			Destroys the upload on the server.
		"""
		self.transport.get("/uploads/%s/destroy" % upload_id)

	def finish_upload(self, upload_id):
		"""
			Signals to the server, that the upload has finished.
		"""
		self.transport.get("/uploads/%s/finished" % upload_id)

	def run(self):
		upload_id = None

		# Create a progress bar.
		progress = pakfire.util.make_progress(
			os.path.basename(self.filename), os.path.getsize(self.filename), speed=True, eta=True,
		)

		try:
			# Get an upload ID.
			upload_id = self.get_upload_id()

			# Send the file content.
			self.send_file(upload_id, progress_callback=progress.update)

		except:
			progress.finish()

			# Remove broken upload from server.
			if upload_id:
				self.destroy_upload(upload_id)

			# XXX catch fatal errors
			raise

		else:
			progress.finish()

			# If no exception was raised, the upload
			# has finished.
			self.finish_upload(upload_id)

		# Return the upload id so some code can actually do something
		# with the file on the server.
		return upload_id


class PakfireHubTransport(object):
	"""
		Connection to the pakfire hub.
	"""

	def __init__(self, config):
		self.config = config

		# Create connection to the hub.
		self.grabber = pakfire.downloader.PakfireGrabber(
			self.config, prefix=self.url,
		)

	def fork(self):
		return self.grabber.fork()

	@property
	def url(self):
		"""
			Construct a right URL out of the given
			server, username and password.

			Basicly this just adds the credentials
			to the URL.
		"""
		# Get credentials.
		server, username, password = self.config.get_hub_credentials()

		# Parse the given URL.
		url = urlparse.urlparse(server)
		assert url.scheme in ("http", "https")

		# Build new URL.
		ret = "%s://" % url.scheme

		# Add credentials if provided.
		if username and password:
			ret += "%s:%s@" % (username, password)

		# Add path components.
		ret += url.netloc

		return ret

	def one_request(self, url, **kwargs):
		try:
			return self.grabber.urlread(url, **kwargs)

		except urlgrabber.grabber.URLGrabError, e:
			# Timeout
			if e.errno == 12:
				raise TransportConnectionTimeoutError, e

			# Handle common HTTP errors
			elif e.errno == 14:
				# Connection errors
				if e.code == 5:
					raise TransportConnectionProxyError, url
				elif e.code == 6:
					raise TransportConnectionDNSError, url
				elif e.code == 7:
					raise TransportConnectionResetError, url
				elif e.code == 23:
					raise TransportConnectionWriteError, url
				elif e.code == 26:
					raise TransportConnectionReadError, url

				# SSL errors
				elif e.code == 52:
					raise TransportSSLCertificateExpiredError, url

				# HTTP error codes
				elif e.code == 403:
					raise TransportForbiddenError, url
				elif e.code == 404:
					raise TransportNotFoundError, url
				elif e.code == 500:
					raise TransportInternalServerError, url
				elif e.code == 504:
					raise TransportConnectionTimeoutError, url

			# All other exceptions...
			raise

	def request(self, url, tries=None, **kwargs):
		# tries = None implies wait infinitely

		while tries or tries is None:
			if tries:
				tries -= 1

			try:
				return self.one_request(url, **kwargs)

			# 500 - Internal Server Error
			except TransportInternalServerError, e:
				log.exception("%s" % e.__class__.__name__)

				# Wait a minute before trying again.
				time.sleep(60)

			# Retry on connection problems.
			except TransportConnectionError, e:
				log.exception("%s" % e.__class__.__name__)

				# Wait for 10 seconds.
				time.sleep(10)

		raise TransportMaxTriesExceededError

	def escape_args(self, **kwargs):
		return urllib.urlencode(kwargs)

	def get(self, url, data={}, **kwargs):
		"""
			Sends a HTTP GET request to the given URL.

			All given keyword arguments are considered as form data.
		"""
		params = self.escape_args(**data)

		if params:
			url = "%s?%s" % (url, params)

		return self.request(url, **kwargs)

	def post(self, url, data={}, **kwargs):
		"""
			Sends a HTTP POST request to the given URL.

			All keyword arguments are considered as form data.
		"""
		params = self.escape_args(**data)
		if params:
			kwargs.update({
				"data" : params,
			})

		return self.request(url, **kwargs)

	def upload_file(self, filename):
		"""
			Uploads the given file to the server.
		"""
		uploader = PakfireHubTransportUploader(self, filename)
		upload_id = uploader.run()

		return upload_id

	def get_json(self, *args, **kwargs):
		res = self.get(*args, **kwargs)

		# Decode JSON.
		if res:
			return json.loads(res)

	### Misc. actions

	def noop(self):
		"""
			No operation. Just to check if the connection is
			working. Returns a random number.
		"""
		return self.get("/noop")

	def test_code(self, error_code):
		assert error_code >= 100 and error_code <= 999

		self.get("/error/test/%s" % error_code)

	# Build actions

	def build_create(self, filename, build_type, arches=None, distro=None):
		"""
			Create a new build on the hub.
		"""
		assert build_type in ("scratch", "release")

		# XXX Check for permission to actually create a build.

		# Upload the source file to the server.
		upload_id = self.upload_file(filename)

		data = {
			"arches"     : ",".join(arches or []),
			"build_type" : build_type,
			"distro"     : distro or "",
			"upload_id"  : upload_id,
		}

		# Then create the build.
		build_id = self.get("/builds/create", data=data)

		return build_id or None

	def build_get(self, build_uuid):
		return self.get_json("/builds/%s" % build_uuid)

	# Job actions

	def job_get(self, job_uuid):
		return self.get_json("/jobs/%s" % job_uuid)

	# Package actions

	def package_get(self, package_uuid):
		return self.get_json("/packages/%s" % package_uuid)
