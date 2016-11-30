#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
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
import json
import logging
import ssl
import time
import urllib.parse
import urllib.request

from .ui import progressbar

from .constants import *
from . import errors

log = logging.getLogger("pakfire.http")
log.propagate = 1

class Client(object):
	"""
		Implements a basic HTTP client which is used to download
		repository data, packages and communicate with the Pakfire Hub.
	"""
	def __init__(self, baseurl=None):
		self.baseurl = baseurl

		# Stores any proxy configuration
		self.proxies = {}

		# Create an SSL context to HTTPS connections
		self.ssl_context = ssl.create_default_context()

	def set_proxy(self, protocol, host):
		"""
			Sets a proxy that will be used to send this request
		"""
		self.proxies[protocol] = host

	def disable_certificate_validation(self):
		# Disable checking hostname
		self.ssl_context.check_hostname = False

		# Disable any certificate validation
		self.ssl_context.verify_mode = ssl.CERT_NONE

	def _make_request(self, url, method="GET", data=None, auth=None):
		# Add the baseurl
		if self.baseurl:
			url = urllib.parse.urljoin(self.baseurl, url)

		# Encode data
		if data:
			data = urllib.parse.urlencode(data)

			# Add data arguments to the URL when using GET
			if method == "GET":
				url += "?%s" % data
				data = None

			# Convert data into Bytes for POST
			elif method == "POST":
				data = bytes(data, "ascii")

		# Create a request
		req = urllib.request.Request(url, data=data)

		# Add our user agent
		req.add_header("User-Agent", "pakfire/%s" % PAKFIRE_VERSION)

		# Add authentication headers
		if auth:
			auth_header = self._make_auth_header(auth)
			req.add_header("Authorization", auth_header)

		# Configure proxies
		for protocol, host in self.proxies.items():
			req.set_proxy(host, protocol)

		# When we send data in a post request, we must set the
		# Content-Length header
		if data and method == "POST":
			req.add_header("Content-Length", len(data))

		# Check if method is correct
		assert method == req.get_method()

		return req

	def _send_request(self, req):
		log.debug("HTTP Request to %s" % req.host)
		log.debug("    URL: %s" % req.full_url)
		log.debug("    Headers:")
		for k, v in req.header_items():
			log.debug("        %s: %s" % (k, v))

		try:
			res = urllib.request.urlopen(req, context=self.ssl_context)

		# Catch any HTTP errors
		except urllib.error.HTTPError as e:
			if e.code == 403:
				raise ForbiddenError()
			elif e.code == 404:
				raise NotFoundError()
			elif e.code == 500:
				raise InternalServerError()
			elif e.code in (502, 503):
				raise BadGatewayError()
			elif e.code == 504:
				raise ConnectionTimeoutError()

			# Raise any unhandled exception
			raise

		log.debug("HTTP Response: %s" % res.code)
		log.debug("    Headers:")
		for k, v in res.getheaders():
			log.debug("        %s: %s" % (k, v))

		return res

	def _one_request(self, url, decode=None, **kwargs):
		r = self._make_request(url, **kwargs)

		# Send request and return the entire response at once
		with self._send_request(r) as f:
			content = f.read()

			# Decode content
			if decode:
				content = self._decode_content(decode, content)

			return content

	def _decode_content(self, type, content):
		assert type in ("json")

		# Decode from bytes to string
		content = content.decode("ascii")

		# Parse JSON
		try:
			if type == "json":
				content = json.loads(content)

		except ValueError as e:
			raise DecodeError() from e

		return content

	def get(self, url, **kwargs):
		"""
			Shortcut to GET content and have it returned
		"""
		return self._one_request(url, method="GET", **kwargs)

	def request(self, url, tries=None, **kwargs):
		# tries = None implies wait infinitely

		while tries is None or tries > 0:
			if tries:
				tries -= 1

			try:
				return self._one_request(url, **kwargs)

			# Bad Gateway Error
			except BadGatewayError as e:
				log.exception("%s" % e.__class__.__name__)

				# Wait a minute before trying again.
				time.sleep(60)

			# Retry on connection problems.
			except ConnectionError as e:
				log.exception("%s" % e.__class__.__name__)

				# Wait for 10 seconds.
				time.sleep(10)

			except (KeyboardInterrupt, SystemExit):
				break

		raise MaxTriesExceededError

	def retrieve(self, url, filename, message=None, **kwargs):
		p = None

		if message is None:
			message = os.path.basename(url)

		buffer_size = 100 * 1024 # 100k

		# Prepare HTTP request
		r = self._make_request(url, **kwargs)

		# Send the request
		with self._make_progressbar(message) as p:
			with self._send_request(r) as f:
				# Try setting progress bar to correct maximum value
				# XXX this might need a function in ProgressBar
				l = self._get_content_length(f)
				p.value_max = l

				while True:
					buf = f.read(buffer_size)
					if not buf:
						break

					l = len(buf)
					p.update_increment(l)

	def _get_content_length(self, response):
		s = response.getheader("Content-Length")

		try:
			return int(s)
		except TypeError:
			pass

	@staticmethod
	def _make_auth_header(auth):
		"""
			Returns a HTTP Basic Authentication header
		"""
		try:
			username, password = auth
		except ValueError:
			raise ValueError("auth takes a tuple with username and password")

		authstring = "%s:%s" % (username, password)

		# Encode into bytes
		authstring = authstring.encode("ascii")

		# Encode into base64
		authstring = base64.b64encode(authstring)

		return "Basic %s" % authstring.decode("ascii")

	def _make_progressbar(self, message=None, **kwargs):
		p = progressbar.ProgressBar(**kwargs)

		# Show message (e.g. filename)
		if message:
			p.add(message)

		# Show percentage
		w = progressbar.WidgetPercentage(clear_when_finished=True)
		p.add(w)

		# Add a bar
		w = progressbar.WidgetBar()
		p.add(w)

		# Show transfer speed
		# XXX just shows the average speed which is probably
		# not what we want here. Might want an average over the
		# last x (maybe ten?) seconds
		w = progressbar.WidgetFileTransferSpeed()
		p.add(w)

		# Spacer
		p.add("|")

		# Show downloaded bytes
		w = progressbar.WidgetBytesReceived()
		p.add(w)

		# ETA
		w = progressbar.WidgetETA()
		p.add(w)

		return p


class HTTPError(errors.Error):
	pass


class ForbiddenError(HTTPError):
	"""
		HTTP Error 403 - Forbidden
	"""
	pass


class NotFoundError(HTTPError):
	"""
		HTTP Error 404 - Not Found
	"""
	pass


class InternalServerError(HTTPError):
	"""
		HTTP Error 500 - Internal Server Error
	"""
	pass


class BadGatewayError(HTTPError):
	"""
		HTTP Error 502+503 - Bad Gateway
	"""
	pass


class ConnectionTimeoutError(HTTPError):
	"""
		HTTP Error 504 - Connection Timeout
	"""
	pass


class ConnectionError(Exception):
	"""
		Raised when there is problems with the connection
		(on an IP sort of level).
	"""
	pass


class SSLError(ConnectionError):
	"""
		Raised when there are any SSL problems.
	"""
	pass


class MaxTriedExceededError(errors.Error):
	"""
		Raised when the maximum number of tries has been exceeded
	"""
	pass


class DecodeError(errors.Error):
	"""
		Raised when received content could not be decoded
		(e.g. JSON)
	"""
	pass
