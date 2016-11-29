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

from . import transport

from pakfire.constants import *
from pakfire.i18n import _

import logging
log = logging.getLogger("pakfire.client")

class PakfireClient(object):
	def __init__(self, config):
		self.config = config

		# Create connection to the hub.
		self.transport = transport.PakfireHubTransport(self.config)

	def build_create(self, *args, **kwargs):
		return self.transport.build_create(*args, **kwargs)

	def build_get(self, *args, **kwargs):
		return self.transport.build_get(*args, **kwargs)

	def job_get(self, *args, **kwargs):
		return self.transport.job_get(*args, **kwargs)

	def package_get(self, *args, **kwargs):
		return self.transport.package_get(*args, **kwargs)
