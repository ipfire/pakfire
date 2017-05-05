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

import json
import lzma
import os

import logging
log = logging.getLogger("pakfire")

from .. import http
from .. import util

from . import base
from . import cache
from . import metadata

from ..constants import *
from ..i18n import _

class RepositoryRemote(base.RepositoryFactory):
	# XXX TODO Make metadata age configureable.

	def init(self, **settings):
		# Save the settings that come from the configuration file
		self.settings = settings

		# Enabled/disable the repository, based on the configuration setting.
		enabled = self.settings.get("enabled", True)
		self.enabled = util.is_enabled(enabled)

	@property
	def baseurl(self):
		return self.settings.get("baseurl")

	@property
	def keyfile(self):
		keyfile = self.settings.get("keyfile", None)

		if keyfile is None:
			keyfile = self.settings.get("gpgkey", None)

		return keyfile

	@property
	def priority(self):
		priority = self.settings.get("priority", None)
		if not priority is None:
			# Try to concert the given input to an integer
			# and return the value if possible.
			try:
				priority = int(priority)
				return priority

			except ValueError:
				pass

		# The default priority is 100.
		priority = 100

		url2priority = {
			"file://" : 50,
			"http://" : 75,
		}

		for url, prio in list(url2priority.items()):
			if self.baseurl.startswith(url):
				priority = prio
				break

		return priority

	def make_downloader(self):
		"""
			Creates a downloader that can be used to download
			metadata, databases or packages from this repository.
		"""
		downloader = http.Client(baseurl=self.baseurl)

		# Add any mirrors that we know of
		for mirror in self.mirrorlist:
			downloader.add_mirror(mirror.get("url"))

		return downloader

	def refresh(self, force=False):
		# Don't do anything if running in offline mode
		if self.pakfire.offline:
			log.debug(_("Skipping refreshing %s since we are running in offline mode") % self)
			return

		# Refresh the mirror list
		self._refresh_mirror_list(force=force)

		# Refresh metadata
		self._refresh_metadata(force=force)

		# Refresh database
		self._refresh_database()

		# Read database
		if self.database:
			self.read_solv(self.database)

	@property
	def mirrorlist(self):
		"""
			Opens a cached mirror list
		"""
		with self.cache_open("mirrors", "r") as f:
			mirrors = json.load(f)

			return mirrors.get("mirrors")

		return []

	def _refresh_mirror_list(self, force=False):
		# Check age of the mirror list first
		age = self.cache_age("mirrors")

		# Don't refresh anything if the mirror list
		# has been refreshed in the last 24 hours
		if not force and age and age <= 24 * 3600:
			return

		# (Re-)download the mirror list
		url = self.settings.get("mirrors", None)
		if not url:
			return

		# Use a generic downloader
		downloader = http.Client()

		# Download a new mirror list
		mirrorlist = downloader.get(url, decode="json")

		# Write new list to disk
		with self.cache_open("mirrors", "w") as f:
			s = json.dumps(mirrorlist)
			f.write(s)

	@property
	def metadata(self):
		if not self.cache_exists("repomd.json"):
			return

		with self.cache_open("repomd.json", "r") as f:
			return metadata.Metadata(self.pakfire, metadata=f.read())

	def _refresh_metadata(self, force=False):
		# Check age of the metadata first
		age = self.cache_age("repomd.json")

		# Don't refresh anything if the metadata
		# has been refresh within the last 10 minutes
		if not force and age and age <= 600:
			return

		# Get a downloader
		downloader = self.make_downloader()

		while True:
			data = downloader.get("%s/repodata/repomd.json" % self.pakfire.arch.name, decode="ascii")

			# Parse new metadata for comparison
			md = metadata.Metadata(self.pakfire, metadata=data)

			if self.metadata and md < self.metadata:
				log.warning(_("The downloaded metadata was less recent than the current one."))
				downloader.skip_current_mirror()
				continue

			# If the download went well, we write the downloaded data to disk
			# and break the loop.
			with self.cache_open("repomd.json", "w") as f:
				md.save(f)

			break

	@property
	def database(self):
		if self.metadata and self.metadata.database and self.cache_exists(self.metadata.database):
			return self.cache_path(self.metadata.database)

	def _refresh_database(self):
		assert self.metadata, "Metadata does not exist"

		# Exit if the file already exists in the cache
		if self.cache_exists(self.metadata.database):
			return

		# Make the downloader
		downloader = self.make_downloader()

		# This is where the file will be saved after download
		path = self.cache_path(self.metadata.database)

		# XXX compare checksum here
		downloader.retrieve("repodata/%s" % self.metadata.database, filename=path,
			message=_("%s: package database") % self.name)

	def download(self, pkg, text="", logger=None):
		"""
			Downloads 'filename' from repository and returns the local filename.
		"""
		if logger is None:
			logger = log

		filename, hash1 = pkg.filename, pkg.hash1

		# Marker, if we need to download the package.
		download = True

		cache_filename = pkg.cache_filename

		# Check if file already exists in cache.
		if self.cache.exists(cache_filename):
			logger.debug("File exists in cache: %s" % filename)

			# If the file does already exist, we check if the hash1 matches.
			if hash1 and self.cache.verify(cache_filename, hash1):
				# We already got the right file. Skip download.
				download = False
			else:
				# The file in cache has a wrong hash. Remove it and repeat download.
				self.cache.remove(cache_filename)

		# Get a package grabber and add mirror download capabilities to it.
		grabber = downloader.PackageDownloader(
			self.pakfire,
			text=text + os.path.basename(filename),
		)
		grabber = self.mirrors.group(grabber)

		# Make sure filename is of type string (and not unicode)
		filename = str(filename)

		while download:
			logger.debug("Going to download %s" % filename)

			# If we are in offline mode, we cannot download any files.
			if self.pakfire.offline and not self.baseurl.startswith("file://"):
				raise OfflineModeError(_("Cannot download this file in offline mode: %s") \
					% filename)

			try:
				i = grabber.urlopen(filename)
			except urlgrabber.grabber.URLGrabError as e:
				raise DownloadError(_("Could not download %s: %s") % (filename, e))

			# Open input and output files and download the file.
			o = self.cache.open(cache_filename, "w")

			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(buf)
				buf = i.read(BUFFER_SIZE)

			i.close()
			o.close()

			# Calc the hash1 of the downloaded file.
			calc_hash1 = self.cache.hash1(cache_filename)

			if calc_hash1 == hash1:
				logger.debug("Successfully downloaded %s (%s)." % (filename, hash1))
				break

			sums = {
				"good" : hash1,
				"bad"  : calc_hash1,
			}

			logger.warning(_("The checksum of the downloaded file did not match."))
			logger.warning(_("Expected %(good)s but got %(bad)s.") % sums)
			logger.warning(_("Trying an other mirror."))

			# Remove the bad file.
			self.cache.remove(cache_filename)

			# Go to the next mirror.
			grabber.increment_mirror(grabber)

		return os.path.join(self.cache.path, cache_filename)

	def get_config(self):
		if self.enabled:
			enabled = "1"
		else:
			enabled = "0"

		lines = [
			"[repo:%s]" % self.name,
			"description = %s" % self.description,
			"enabled = %s" % enabled,
			"baseurl = %s" % self.baseurl,
		]

		mirrors = self.settings.get("mirrors", None)
		if mirrors:
			lines.append("mirrors = %s" % mirrors)

		lines += [
			#"gpgkey = %s" % self.keyfile,
			"priority = %s" % self.priority,
		]

		return lines
