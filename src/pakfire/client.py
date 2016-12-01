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

import logging

from .ui.helpers import format_time

from . import config
from . import hub

from .constants import *
from .i18n import _

log = logging.getLogger("pakfire.client")
log.propagate = 1

class Client(object):
	def __init__(self, config_file="client.conf"):
		# Read configuration
		self.config = config.Config(config_file)

		# Create connection to the hub
		self.hub = self.connect_to_hub()

	def connect_to_hub(self):
		huburl = self.config.get("client", "server", PAKFIRE_HUB)

		# User Credentials
		username = self.config.get("client", "username")
		password = self.config.get("client", "password")

		if not (username and password):
			raise RuntimeError("User credentials are not set")

		# Create connection to the hub.
		return hub.Hub(huburl, username, password)

	def create_build(self, filename, **kwargs):
		build_id = self.hub.create_build(filename, **kwargs)

		return self.get_build(build_id)

	def get_build(self, build_id):
		return Build(self, build_id)


class _ClientObject(object):
	def __init__(self, client, id):
		self.client = client

		# UUID of the build
		self.id = id

		self._data = None
		self._cache = {}

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.id)

	def __eq__(self, other):
		return self.id == other.id

	@property
	def data(self):
		if self._data is None:
			self._data = self._load()

		return self._data

	def refresh(self):
		self._data = self._load()

	def _load(self):
		"""
			Loads information about this object from the hub
		"""
		raise NotImplementedError


class Build(_ClientObject):
	def _load(self):
		"""
			Loads information about this build from the hub
		"""
		return self.client.hub.get_build(self.id)

	@property
	def jobs(self):
		jobs = []

		for job in self.data.get("jobs"):
			try:
				j = self._cache[job]
			except KeyError:
				j = Job(self.client, job)

			jobs.append(j)

		return sorted(jobs)

	@property
	def type(self):
		"""
			The type of this build (release or scratch)
		"""
		return self.data.get("type")

	@property
	def _type_tag(self):
		if self.type == "release":
			return "[R]"

		elif self.type == "scratch":
			return "[S]"

	@property
	def name(self):
		"""
			The name of this build
		"""
		return self.data.get("name")

	@property
	def priority(self):
		"""
			The priority of this build
		"""
		return self.data.get("priority")

	@property
	def score(self):
		"""
			The score of this build
		"""
		return self.data.get("score")

	@property
	def state(self):
		"""
			The state this build is in
		"""
		return self.data.get("state")

	def is_active(self):
		return self.state == "building"

	@property
	def oneline(self):
		s = [
			self.name,
			self._type_tag,
			"(%s)" % self.id,
			_("Score: %s") % self.score,
			_("Priority: %s") % self.priority,
		]

		return " ".join(s)

	def dump(self):
		# Add a headline for the build
		s = [
			self.oneline,
		]

		# Add a short line for each job
		for j in self.jobs:
			s.append("  %s" % j.oneline)

		return "\n".join(s)


class Job(_ClientObject):
	def _load(self):
		"""
			Loads information about this job from the hub
		"""
		return self.client.hub.get_job(self.id)

	def __lt__(self, other):
		return self.arch < other.arch

	@property
	def arch(self):
		"""
			The architecture of this job
		"""
		return self.data.get("arch")

	@property
	def builder(self):
		"""
			The name of the builder that built this job
		"""
		return self.data.get("builder")

	@property
	def duration(self):
		"""
			The duration the job took to build
		"""
		return self.data.get("duration")

	@property
	def state(self):
		"""
			The state of this job
		"""
		return self.data.get("state")

	def is_active(self):
		return self.state in ("dispatching", "running", "uploading")

	def is_finished(self):
		return self.state == "finished"

	@property
	def oneline(self):
		s = [
			# Architecture
			"[%-8s]" % self.arch,

			# State
			"[%12s]" % self.state,
		]

		if self.is_active():
			s.append(_("on %s") % self.builder)

		elif self.is_finished():
			s.append(_("in %s") % format_time(self.duration))

		return " ".join(s)
