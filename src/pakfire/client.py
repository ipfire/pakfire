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

# XXX OLD CODE

class PakfireUserClient(PakfireClient):
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

