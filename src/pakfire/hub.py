#!/usr/bin/python3
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

import base64
import hashlib
import logging
import math
import os.path
import time

from . import http

from .constants import *

log = logging.getLogger("pakfire.hub")
log.propagate = 1

class Hub(object):
	def __init__(self, huburl, username, password):
		self.username = username
		self.password = password
		print(huburl)

		# Initialise the HTTP client
		self.http = http.Client(baseurl=huburl)

	def _request(self, *args, **kwargs):
		"""
			Wrapper function around the HTTP Client request()
			function that adds authentication, etc.
		"""
		kwargs.update({
			"auth" : (self.username, self.password),
		})

		return self.http.request(*args, **kwargs)

	# Test functions

	def test(self):
		"""
			Tests the connection
		"""
		return self._request("/noop")

	def test_error(self, code):
		assert code >= 100 and code <= 999

		self._request("/error/test/%s" % code)

	# Build actions

	def get_build(self, uuid):
		return self._request("/builds/%s" % uuid, decode="json")

	def create_build(self, path, type, arches=None, distro=None):
		"""
			Create a new build on the hub
		"""
		assert type in ("scratch", "release")

		# XXX Check for permission to actually create a build

		# Upload the souce file to the server
		upload_id = self.upload_file(path)

		data = {
			"arches"     : ",".join(arches or []),
			"build_type" : type,
			"distro"     : distro or "",
			"upload_id"  : upload_id,
		}

		build_id = self._request("/builds/create", data=data)

		return build_id

	# Job actions

	def get_job(self, uuid):
		return self._request("/jobs/%s" % uuid, decode="json")

	# Package actions

	def get_package(self, uuid):
		return self._request("/packages/%s" % uuid, decode="json")

	# File uploads

	def upload_file(self, path):
		uploader = FileUploader(self, path)

		return uploader.upload()


class FileUploader(object):
	"""
		Handles file uploads to the Pakfire Hub
	"""
	def __init__(self, hub, path):
		self.hub = hub
		self.path = path

	@property
	def filename(self):
		"""
			Returns the basename of the uploaded file
		"""
		return os.path.basename(self.path)

	@property
	def filesize(self):
		"""
			The filesize of the uploaded file
		"""
		return os.path.getsize(self.path)

	@staticmethod
	def _make_checksum(algo, path):
		h = hashlib.new(algo)

		with open(path, "rb") as f:
			while True:
				buf = f.read(CHUNK_SIZE)
				if not buf:
					break

				h.update(buf)

		return h.hexdigest()

	def _get_upload_id(self):
		"""
			Sends some basic information to the hub
			and requests an upload id.
		"""
		data = {
			"filename" : self.filename,
			"filesize" : self.filesize,
			"hash"     : self._make_checksum("sha1", self.path),
		}

		response = self.hub._request("/uploads/create", method="GET", data=data)

		return response.decode("ascii")

	def _send_chunk(self, upload_id, chunk):
		"""
			Sends a chunk at a time
		"""
		# Compute the SHA512 checksum of this chunk
		h = hashlib.new("sha512")
		h.update(chunk)

		# Encode data in base64
		data = base64.b64encode(chunk)

		# Send chunk to the server
		self.hub._request("/uploads/%s/sendchunk" % upload_id, method="POST",
			data={ "chksum" : h.hexdigest(), "data" : data })

		return len(chunk)

	def upload(self):
		"""
			Main function which runs the upload
		"""
		# Borrow progressbar from downloader
		p = self.hub.http._make_progressbar(message=self.filename, value_max=self.filesize)

		with p:
			# Request an upload ID
			upload_id = self._get_upload_id()
			assert upload_id

			log.debug("Starting upload with id %s" % upload_id)

			# Initial chunk size
			chunk_size = CHUNK_SIZE

			try:
				with open(self.path, "rb") as f:
					while True:
						chunk = f.read(chunk_size)
						if not chunk:
							break

						# Save the time when we started to send this bit
						time_started = time.time()

						# Send the chunk to the server
						self._send_chunk(upload_id, chunk)

						# Determine the size of the next chunk
						duration = time_started - time.time()
						chunk_size = math.ceil(chunk_size / duration)

						# Never let chunk_size drop under CHUNK_SIZE
						if chunk_size < CHUNK_SIZE:
							chunk_size = CHUNK_SIZE

						# Update progressbar
						p.update_increment(len(chunk))

			# Catch any unhandled exception here, tell the hub to delete the
			# file and raise the original exception
			except Exception as e:
				self.hub._request("/uploads/%s/destroy" % upload_id)

				raise

			# If all went well, we finish the upload
			else:
				self.hub._request("/uploads/%s/finished" % upload_id)

				# Return the upload ID if the upload was successful
				return upload_id
