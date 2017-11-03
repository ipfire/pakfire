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

		# Initialise the HTTP client
		self.http = http.Client(baseurl=huburl)

	@property
	def _request_args(self):
		"""
			Arguments sent with each request
		"""
		return {
			"auth" : (self.username, self.password),
		}

	def _request(self, *args, **kwargs):
		"""
			Wrapper function around the HTTP Client request()
			function that adds authentication, etc.
		"""
		kwargs.update(self._request_args)

		return self.http.request(*args, **kwargs)

	def _upload(self, *args, **kwargs):
		kwargs.update(self._request_args)

		return self.http.upload(*args, **kwargs)

	# Test functions

	def test(self):
		"""
			Tests the connection
		"""
		return self._request("/noop", decode="ascii")

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

		return self._request("/builds/create", data=data, decode="ascii")

	# Job actions

	def get_job(self, uuid):
		return self._request("/jobs/%s" % uuid, decode="json")

	# Package actions

	def get_package(self, uuid):
		return self._request("/packages/%s" % uuid, decode="json")

	# File uploads

	def upload_file(self, path):
		# Send some basic information to the hub
		# and request an upload ID
		data = {
			"filename" : os.path.basename(path),
			"filesize" : os.path.getsize(path),
		}
		upload_id = self._request("/uploads/create", method="GET",
			decode="ascii", data=data)

		log.debug("Upload ID: %s" % upload_id)

		# Upload the data
		self._upload("/uploads/stream?id=%s" % upload_id, path)

		return upload_id