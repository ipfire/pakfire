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

import os
import urlgrabber

import logging
log = logging.getLogger("pakfire")

import base
import cache
import metadata

import pakfire.compress as compress
import pakfire.downloader as downloader

from pakfire.constants import *
from pakfire.i18n import _

class RepositoryRemote(base.RepositoryFactory):
	# XXX TODO Make metadata age configureable.

	def __init__(self, pakfire, name, description=None, **settings):
		# Save the settings that come from the configuration file.
		self.settings = settings

		base.RepositoryFactory.__init__(self, pakfire, name, description)

		# Enabled/disable the repository, based on the configuration setting.
		enabled = self.settings.get("enabled", True)
		if enabled in ("1", "yes", "on", True, 1):
			self.enabled = True
		else:
			self.enabled = False

		# Create an cache object
		self.cache = cache.RepositoryCache(self.pakfire, self)

		# Initialize mirror servers.
		mirrorlist = self.settings.get("mirrors", None)
		self.mirrors = downloader.MirrorList(self.pakfire, self, mirrorlist)

		# Open metadata if any.
		self.metadata = self.open_metadata()

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

		for url, prio in url2priority.items():
			if self.baseurl.startswith(url):
				priority = prio
				break

		return priority

	def cache_path(self, *paths):
		return os.path.join(
			"repodata",
			self.distro.sname,
			self.distro.release,
			self.name,
			self.distro.arch,
			*paths
		)

	def clean(self):
		RepositoryFactory.clean(self)

		# Remove all files in the files cache.
		self.cache.destroy()

	def update(self, force=False, offline=False):
		if force and offline:
			raise OfflineModeError, _("You cannot force to update metadata in offline mode.")

		# First update the repository metadata.
		self.update_metadata(force=force, offline=offline)
		self.update_database(force=force, offline=offline)

		# Read the database.
		self.open_database()

	def open_metadata(self, path=None):
		if not path:
			path = self.cache_path(os.path.basename(METADATA_DOWNLOAD_FILE))
			path = self.cache.abspath(path)

		if self.cache.exists(path):
			return metadata.Metadata(self.pakfire, path)

	def update_metadata(self, force=False, offline=False):
		filename = os.path.join(METADATA_DOWNLOAD_PATH, METADATA_DOWNLOAD_FILE)
		cache_filename = self.cache_path(os.path.basename(filename))

		# Check if the metadata is already recent enough...
		exists = self.cache.exists(cache_filename)

		if not exists and offline:
			raise OfflineModeError, _("No metadata available for repository %s. Cannot download any.") \
				% self.name

		elif exists and offline:
			# Repository metadata exists. We cannot update anything because of the offline mode.
			return

		if not force and exists:
			age = self.cache.age(cache_filename)
			if age and age < TIME_10M:
				log.debug("Metadata is recent enough. I don't download it again.")
				return

		# Going to download metada.
		log.debug("Going to download repository metadata for %s..." % self.name)
		assert not offline

		grabber = downloader.MetadataDownloader(self.pakfire)
		grabber = self.mirrors.group(grabber)

		while True:
			try:
				data = grabber.urlread(filename, limit=METADATA_DOWNLOAD_LIMIT)
			except urlgrabber.grabber.URLGrabError, e:
				if e.errno == 256:
					raise DownloadError, _("Could not update metadata for %s from any mirror server") % self.name

				grabber.increment_mirror(grabber)
				continue

			# Parse new metadata for comparison.
			md = metadata.Metadata(self.pakfire, metadata=data)

			if self.metadata and md < self.metadata:
				log.warning(_("The downloaded metadata was less recent than the current one."))
				grabber.increment_mirror(grabber)
				continue

			# If the download went well, we write the downloaded data to disk
			# and break the loop.
			f = self.cache.open(cache_filename, "w")
			f.write(data)
			f.close()

			break

		# Re-open metadata.
		self.metadata = self.open_metadata()
		assert self.metadata

	def open_database(self):
		assert self.metadata, "Metadata needs to be openend first."

		filename = self.cache_path("database", self.metadata.database)
		filename = self.cache.abspath(filename)

		assert os.path.exists(filename)

		self.index.clear()
		self.index.read(filename)

	def update_database(self, force=False, offline=False):
		assert self.metadata, "Metadata needs to be openend first."

		# Construct cache and download filename.
		filename = os.path.join(METADATA_DOWNLOAD_PATH, self.metadata.database)
		cache_filename = self.cache_path("database", self.metadata.database)

		if not force:
			force = not self.cache.exists(cache_filename)

		# Raise an exception when we are running in offline mode but an update is required.
		if force and offline:
			raise OfflineModeError, _("Cannot download package database for %s in offline mode.") % self.name

		elif not force:
			return

		# Just make sure we don't try to download anything in offline mode.
		assert not offline

		# Initialize a grabber for download.
		grabber = downloader.DatabaseDownloader(
			self.pakfire,
			text = _("%s: package database") % self.name,
		)
		grabber = self.mirrors.group(grabber)

		while True:
			# Open file on server.
			urlobj = fileobj = grabber.urlopen(filename)

			if self.metadata.database_compression:
				fileobj = compress.decompressobj(fileobj=fileobj,
					algo=self.metadata.database_compression)

			# Make a new file in the cache.
			cacheobj = self.cache.open(cache_filename, "wb")

			try:
				while True:
					buf = fileobj.read(BUFFER_SIZE)
					if not buf:
						break
					cacheobj.write(buf)

			finally:
				# XXX we should catch decompression errors

				# Close all file descriptors.
				cacheobj.close()
				fileobj.close()
				if not urlobj == fileobj:
					urlobj.close()

			break

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
				raise OfflineModeError, _("Cannot download this file in offline mode: %s") \
					% filename

			try:
				i = grabber.urlopen(filename)
			except urlgrabber.grabber.URLGrabError, e:
				raise DownloadError, _("Could not download %s: %s") % (filename, e)

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

		if self.mirrors.mirrorlist:
			lines.append("mirrors = %s" % self.mirrors.mirrorlist)

		lines += [
			#"gpgkey = %s" % self.keyfile,
			"priority = %s" % self.priority,
		]

		return lines
