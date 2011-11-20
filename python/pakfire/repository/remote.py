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

import logging
log = logging.getLogger("pakfire")

import base
import index

import pakfire.downloader as downloader

from pakfire.constants import *
from pakfire.i18n import _

class RepositorySolv(base.RepositoryFactory):
	def __init__(self, pakfire, name, description, url, mirrorlist, gpgkey, enabled=True):
		# Parse arguments.
		self.url = url
		self.gpgkey = gpgkey
		self.mirrorlist = mirrorlist

		base.RepositoryFactory.__init__(self, pakfire, name, description)

		# Initialize mirror servers.
		self.mirrors = downloader.MirrorList(self.pakfire, self)

		# Create index, which is always SOLV.
		self.index = index.IndexSolv(self.pakfire, self)

		# Save enabled/disabled flag at the end.
		if enabled in ("1", "yes", "on", True, 1):
			self.enabled = True
		else:
			self.enabled = False

	@property
	def priority(self):
		priority = 100

		url2priority = {
			"file://" : 50,
			"http://" : 75,
		}

		for url, prio in url2priority.items():
			if self.url.startswith(url):
				priority = prio
				break

		return priority

	def download(self, pkg, text=""):
		"""
			Downloads 'filename' from repository and returns the local filename.
		"""
		filename, hash1 = pkg.filename, pkg.hash1

		# Marker, if we need to download the package.
		download = True

		cache_prefix = ""
		if filename.endswith(PACKAGE_EXTENSION):
			cache_prefix = "packages"
		elif filename == METADATA_DOWNLOAD_FILE:
			cache_prefix = "repodata"
		elif filename.endswith(METADATA_DATABASE_FILE):
			cache_prefix = "repodata"

		cache_filename = os.path.join(cache_prefix, os.path.basename(filename))

		# Check if file already exists in cache.
		if self.cache.exists(cache_filename):
			log.debug("File exists in cache: %s" % filename)

			# If the file does already exist, we check if the hash1 matches.
			if hash1 and self.cache.verify(cache_filename, hash1):
				# We already got the right file. Skip download.
				download = False
			else:
				# The file in cache has a wrong hash. Remove it and repeat download.
				cache.remove(cache_filename)

		if download:
			log.debug("Going to download %s" % filename)

			# If we are in offline mode, we cannot download any files.
			if self.pakfire.offline and not self.url.startswith("file://"):
				raise OfflineModeError, _("Cannot download this file in offline mode: %s") \
					% filename

			# Make sure filename is of type string (and not unicode)
			filename = str(filename)

			# Get a package grabber and add mirror download capabilities to it.
			grabber = downloader.PackageDownloader(
				self.pakfire,
				text=text + os.path.basename(filename),
			)
			grabber = self.mirrors.group(grabber)

			i = grabber.urlopen(filename)

			# Open input and output files and download the file.
			o = self.cache.open(cache_filename, "w")

			buf = i.read(BUFFER_SIZE)
			while buf:
				o.write(buf)
				buf = i.read(BUFFER_SIZE)

			i.close()
			o.close()

			# Verify if the download was okay.
			if hash1 and not self.cache.verify(cache_filename, hash1):
				raise Exception, "XXX this should never happen..."

		return os.path.join(self.cache.path, cache_filename)
