#!/usr/bin/python
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

import socket
import time
import xmlrpclib

import logging
log = logging.getLogger("pakfire.client")

from pakfire.constants import *
from pakfire.i18n import _

class XMLRPCMixin:
	user_agent = "pakfire/%s" % PAKFIRE_VERSION

	def single_request(self, *args, **kwargs):
		ret = None

		# Tries can be passed to this method.
		tries = kwargs.pop("tries", 100)
		timeout = 1

		while tries:
			try:
				ret = xmlrpclib.Transport.single_request(self, *args, **kwargs)

			except socket.error, e:
				# These kinds of errors are not fatal, but they can happen on
				# a bad internet connection or whatever.
				#   32 Broken pipe
				#  110 Connection timeout
				#  111 Connection refused
				if not e.errno in (32, 110, 111,):
					raise

				log.warning(_("Socket error: %s") % e)

			except xmlrpclib.ProtocolError, e:
				# Log all XMLRPC protocol errors.
				log.error("XMLRPC protocol error:")
				log.error("  URL: %s" % e.url)
				log.error("  HTTP headers:")
				for header in e.headers.items():
					log.error("    %s: %s" % header)
				log.error("  Error code: %s" % e.errcode)
				log.error("  Error message: %s" % e.errmsg)
				raise

			else:
				# If request was successful, we can break the loop.
				break

			# If the request was not successful, we wait a little time to try
			# it again.
			tries -= 1
			timeout *= 2
			if timeout > 60:
				timeout = 60

			log.warning(_("Trying again in %s seconds. %s tries left.") % (timeout, tries))
			time.sleep(timeout)

		else:
			log.error("Maximum number of tries was reached. Giving up.")
			# XXX need better exception here.
			raise Exception, "Could not fulfill request."

		return ret


class XMLRPCTransport(XMLRPCMixin, xmlrpclib.Transport):
	"""
		Handles the XMLRPC connection over HTTP.
	"""
	pass


class SafeXMLRPCTransport(XMLRPCMixin, xmlrpclib.SafeTransport):
	"""
		Handles the XMLRPC connection over HTTPS.
	"""
	pass


class Connection(xmlrpclib.ServerProxy):
	"""
		Class wrapper that automatically chooses the right transport
		method depending on the given URL.
	"""

	def __init__(self, url):
		# Create transport channel to the server.
		if url.startswith("https://"):
			transport = SafeXMLRPCTransport()
		elif url.startswith("http://"):
			transport = XMLRPCTransport()

		xmlrpclib.ServerProxy.__init__(self, url, transport=transport,
			allow_none=True)
