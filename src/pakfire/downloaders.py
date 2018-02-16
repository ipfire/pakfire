#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2018 Pakfire development team                                 #
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
import logging

from . import http
from .repository import metadata
from .i18n import _

log = logging.getLogger("pakfire.downloader")
log.propagate = 1

class Downloader(object):
	pass


class RepositoryDownloader(Downloader):
	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

	def make_downloader(self):
		"""
			Creates a downloader that can be used to download
			metadata, databases or packages from this repository.
		"""
		downloader = http.Client(baseurl=self.repo.baseurl)

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
			self.repo.read_solv(self.database)

	@property
	def mirrorlist(self):
		"""
			Opens a cached mirror list
		"""
		try:
			with self.repo.cache_open("mirrors", "r") as f:
				mirrors = json.load(f)

				return mirrors.get("mirrors")

		# If there is no mirror list in the cache,
		# we won't be able to open it
		except IOError:
			pass

		return []

	def _refresh_mirror_list(self, force=False):
		# Check age of the mirror list first
		age = self.repo.cache_age("mirrors")

		# Don't refresh anything if the mirror list
		# has been refreshed in the last 24 hours
		if not force and age and age <= 24 * 3600:
			return

		# (Re-)download the mirror list
		if not self.repo.mirrorlist:
			return

		# Use a generic downloader
		downloader = http.Client()

		# Download a new mirror list
		mirrorlist = downloader.get(self.repo.mirrorlist, decode="json")

		# Write new list to disk
		with self.repo.cache_open("mirrors", "w") as f:
			s = json.dumps(mirrorlist)
			f.write(s)

	@property
	def metadata(self):
		if not self.repo.cache_exists("repomd.json"):
			return

		with self.repo.cache_open("repomd.json", "r") as f:
			return metadata.Metadata(self.pakfire, metadata=f.read())

	def _refresh_metadata(self, force=False):
		# Check age of the metadata first
		age = self.repo.cache_age("repomd.json")

		# Don't refresh anything if the metadata
		# has been refresh within the last 10 minutes
		if not force and age and age <= 600:
			return

		# Get a downloader
		downloader = self.make_downloader()

		while True:
			data = downloader.get("%s/repodata/repomd.json" % self.pakfire.arch, decode="ascii")

			# Parse new metadata for comparison
			md = metadata.Metadata(self.pakfire, metadata=data)

			if self.metadata and md < self.metadata:
				log.warning(_("The downloaded metadata was less recent than the current one."))
				downloader.skip_current_mirror()
				continue

			# If the download went well, we write the downloaded data to disk
			# and break the loop.
			with self.repo.cache_open("repomd.json", "w") as f:
				md.save(f)

			break

	@property
	def database(self):
		if self.metadata and self.metadata.database and self.repo.cache_exists(self.metadata.database):
			return self.repo.cache_path(self.metadata.database)

	def _refresh_database(self):
		assert self.metadata, "Metadata does not exist"

		# Exit if the file already exists in the cache
		if self.repo.cache_exists(self.metadata.database):
			return

		# Make the downloader
		downloader = self.make_downloader()

		# This is where the file will be saved after download
		path = self.repo.cache_path(self.metadata.database)

		# XXX compare checksum here
		downloader.retrieve("repodata/%s" % self.metadata.database, filename=path,
			message=_("%s: package database") % self.repo.name)

	def download_package(self, pkg):
		"""
			Downloads a package to it's cache path
		"""
		downloader = self.make_downloader()

		downloader.retrieve(pkg.filename, filename=pkg.cache_path,
			message="%s" % pkg, checksum_algo="sha1", checksum=pkg.checksum)


class TransactionDownloader(Downloader):
	def __init__(self, pakfire, transaction):
		self.pakfire = pakfire

		# The transaction that we process
		self.transaction = transaction

		# Cache repository downloaders
		self._repo_downloaders = {}

	def _get_repo_downloader(self, repo):
		try:
			return self._repo_downloaders[repo]
		except KeyError:
			d = RepositoryDownloader(self.pakfire, repo)
			self._repo_downloaders[repo] = d

			return d

	def download(self):
		for step in self.transaction:
			# Skip any steps that do not need a download
			if not step.needs_download:
				continue

			# Get the downloader
			downloader = self._get_repo_downloader(step.package.repo)

			# Download the package
			downloader.download_package(step.package)
