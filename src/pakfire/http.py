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
import fcntl
import json
import logging
import ssl
import time
import urllib.parse
import urllib.request

from .ui import progressbar

from .config import config
from .constants import *
from .i18n import _
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

		# Save all mirrors
		self.mirrors = []

		# Save a working copy of the mirror list which is modified
		# when there is a problem with one of the mirrors
		self._mirrors = []

		# Pointer to the current mirror
		self._mirror = None

		# Stores any proxy configuration
		self.proxies = {}

		# Create an SSL context to HTTPS connections
		self.ssl_context = ssl.create_default_context()

		# Configure upstream proxies
		proxy = config.get("downloader", "proxy")
		if proxy:
			for protocol in ("http", "https", "ftp"):
				self.set_proxy(protocol, proxy)

		# Should we verify SSL certificates?
		verify = config.get_bool("downloader", "verify", True)
		if not verify:
			self.disable_certificate_verification()

	def set_proxy(self, protocol, host):
		"""
			Sets a proxy that will be used to send this request
		"""
		self.proxies[protocol] = host

	def disable_certificate_verification(self):
		# Disable checking hostname
		self.ssl_context.check_hostname = False

		# Disable any certificate validation
		self.ssl_context.verify_mode = ssl.CERT_NONE

	def add_mirror(self, mirror, priority=None):
		"""
			Adds a mirror to the mirror list
		"""
		if priority is None:
			priority = 10

		# Create a Mirror object
		m = Mirror(mirror, priority)

		# Append it to the mirror list
		self.mirrors.append(m)

		# Add it to the copy of the list that we use to
		# remove unusable mirrors and sort it to put the
		# new mirror to the right position
		self._mirrors.append(m)
		self._mirrors.sort()

	@property
	def mirror(self):
		"""
			Returns the current mirror that should be used
		"""
		return self._mirror

	def _next_mirror(self):
		"""
			Called when the current mirror is for any reason
			unusable and the next in line should be used.
		"""
		# Use the first mirror from the list until the list is empty
		try:
			self._mirror = self._mirrors.pop(0)

			log.debug(_("Selected mirror: %s") % self._mirror)

		# Raise a download error if no mirror is left
		except IndexError as e:
			raise DownloadError(_("No more mirrors to try")) from e

	def _make_request(self, url, method="GET", data=None, auth=None, baseurl=None, mirror=None):
		# If a mirror is given, we use it as baseurl
		if mirror:
			baseurl = self.mirror.url

		# Add the baseurl to the URL
		if baseurl or self.baseurl:
			url = urllib.parse.urljoin(baseurl or self.baseurl, url)

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

	def _send_request(self, req, timeout=None):
		log.debug("HTTP Request to %s" % req.host)
		log.debug("    URL: %s" % req.full_url)
		log.debug("    Headers:")
		for k, v in req.header_items():
			log.debug("        %s: %s" % (k, v))

		try:
			res = urllib.request.urlopen(req, context=self.ssl_context, timeout=timeout)

		# Catch any HTTP errors
		except urllib.error.HTTPError as e:
			log.debug("HTTP Response: %s" % e.code)

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

	def _one_request(self, url, decode=None, timeout=None, **kwargs):
		r = self._make_request(url, **kwargs)

		# Send request and return the entire response at once
		with self._send_request(r, timeout=timeout) as f:
			content = f.read()

			# Decode content
			if decode:
				content = self._decode_content(decode, content)

			return content

	def _decode_content(self, type, content):
		assert type in ("ascii", "json")

		# Decode from bytes to string
		content = content.decode("ascii")

		try:
			# Parse JSON
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
				return self._request(url, **kwargs)

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
		skipped_mirrors = []

		if message is None:
			message = os.path.basename(url)

		# Initialize mirrors if not done, yet
		if self.mirrors and not self.mirror:
			self._next_mirror()

		try:
			while True:
				with self._make_progressbar(message) as p:
					with open(filename, "wb") as f:
						# Exclusively lock the file for download
						try:
							fcntl.flock(f, fcntl.LOCK_EX)
						except OSError as e:
							raise DownloadError(_("Could not lock target file")) from e

						# Prepare HTTP request
						r = self._make_request(url, mirror=self.mirror, **kwargs)

						try:
							with self._send_request(r) as res:
								# Try setting progress bar to correct maximum value
								# XXX this might need a function in ProgressBar
								l = self._get_content_length(res)
								p.value_max = l

								while True:
									buf = res.read(BUFFER_SIZE)
									if not buf:
										break

									# Write downloaded data to file
									f.write(buf)

									l = len(buf)
									p.increment(l)

								# If the download succeeded, we will
								# break the loop
								break

						except HTTPError as e:
							# If we have mirrors, we will try using the next one
							if self.mirrors:
								skipped_mirrors.append(self.mirror)
								self._next_mirror()
								continue

							# Otherwise raise this error
							raise e

		finally:
			# Re-add any skipped mirrors again so that the next
			# request will be tried on all mirrors, too.
			# The current mirror is being kept.
			self._mirrors += skipped_mirrors

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


class Mirror(object):
	def __init__(self, url, priority=10):
		# URLs must end with a slash for joining
		if not url.endswith("/"):
			url = "%s/" % url

		self.url = url
		self.priority = priority

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.url)

	def __str__(self):
		return self.url

	def __eq__(self, other):
		return self.url == other.url

	def __lt__(self, other):
		return self.priority < other.priority



class DownloadError(errors.Error):
	"""
		Raised when a download was not successful
		(for any reason)
	"""
	pass


class HTTPError(DownloadError):
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
