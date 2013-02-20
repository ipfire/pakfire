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

import httplib
import socket
import ssl
import time
import xmlrpclib

import logging
log = logging.getLogger("pakfire.client")

from pakfire.constants import *
from pakfire.i18n import _

# Set the default socket timeout to 30 seconds.
socket.setdefaulttimeout(30)




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

			# Catch errors related to the connection. Just try again.
			except (socket.error, ssl.SSLError), e:
				log.warning("Exception: %s: %s" % (e.__class__.__name__, e))

			# Presumably, the server closed the connection before sending anything.
			except httplib.BadStatusLine:
				# Try again immediately.
				continue

			# The XML reponse could not be parsed.
			except xmlrpclib.ResponseError, e:
				log.warning("Exception: %s: %s" % (e.__class__.__name__, e))

			except xmlrpclib.ProtocolError, e:
				if e.errcode == 403:
					# Possibly, the user credentials are invalid.
					# Cannot go on.
					raise XMLRPCForbiddenError(e)

				elif e.errcode == 404:
					# Some invalid URL was called.
					# Cannot go on.
					raise XMLRPCNotFoundError(e)

				elif e.errcode == 500:
					# This could have various reasons, so we can not
					# be sure to kill connections here.
					# But to visualize the issue, we will raise an
					# exception on the last try.
					if tries == 1:
						raise XMLRPCInternalServerError(e)

				elif e.errcode == 503:
					# Possibly the hub is not running but the SSL proxy
					# is. Just try again in a short time.
					pass

				else:
					# Log all XMLRPC protocol errors.
					log.error(_("XMLRPC protocol error:"))
					log.error("  %s" % _("URL: %s") % e.url)
					log.error("  %s" % _("  HTTP headers:"))
					for header in e.headers.items():
						log.error("    %s: %s" % header)
					log.error("  %s" % _("Error code: %s") % e.errcode)
					log.error("  %s" % _("Error message: %s") % e.errmsg)

					# If an unhandled error code appeared, we raise an
					# error.
					raise

			except xmlrpclib.Fault:
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

			log.warning(_("Trying again in %(timeout)s second(s). %(tries)s tries left.") \
				% { "timeout" : timeout, "tries" : tries })
			time.sleep(timeout)

		else:
			raise XMLRPCTransportError, _("Maximum number of tries was reached. Giving up.")

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
