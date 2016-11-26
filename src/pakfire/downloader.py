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

import json
import os
import random
import urllib

import logging
log = logging.getLogger("pakfire")

from . import progressbar

from pakfire.constants import *
from pakfire.i18n import _

class PakfireDownloader(object):
	def __init__(self):
		pass

	@property
	def user_agent(self):
		return "pakfire/%s" % PAKFIRE_VERSION

	def set_proxy(self, *args, **kwargs):
		pass

	def use_mirrors(self, mirrors):
		pass


class PackageDownloader(PakfireGrabber):
	def __init__(self, pakfire, *args, **kwargs):
		kwargs.update({
			"progress_obj" : TextMeter(),
		})

		PakfireGrabber.__init__(self, pakfire, *args, **kwargs)


class MetadataDownloader(PakfireGrabber):
	def __init__(self, pakfire, *args, **kwargs):
		kwargs.update({
			"http_headers" : (('Pragma', 'no-cache'),),
		})

		PakfireGrabber.__init__(self, pakfire, *args, **kwargs)


class DatabaseDownloader(PackageDownloader):
	def __init__(self, pakfire, *args, **kwargs):
		kwargs.update({
			"http_headers" : (('Pragma', 'no-cache'),),
		})

		PackageDownloader.__init__(self, pakfire, *args, **kwargs)


class SourceDownloader(object):
	def __init__(self, pakfire, mirrors=None):
		self.pakfire = pakfire

		self.grabber = PakfireGrabber(
			self.pakfire,
			progress_obj = TextMeter(),
		)

		if mirrors:
			self.grabber = MirrorGroup(self.grabber,
				[{ "mirror" : m.encode("utf-8") } for m in mirrors])

	def download(self, files):
		existant_files = []
		download_files = []

		for file in files:
			filename = os.path.join(SOURCE_CACHE_DIR, file)
			log.debug("Checking existance of %s..." % filename)

			if os.path.exists(filename) and os.path.getsize(filename):
				log.debug("...exists!")
				existant_files.append(filename)
			else:
				log.debug("...does not exist!")
				download_files.append(filename)

		if download_files:
			log.info(_("Downloading source files:"))

			if self.pakfire.offline:
				raise OfflineModeError(_("Cannot download source code in offline mode."))

			# Create source download directory.
			if not os.path.exists(SOURCE_CACHE_DIR):
				os.makedirs(SOURCE_CACHE_DIR)

			for filename in download_files:
				try:
					self.grabber.urlgrab(os.path.basename(filename), filename=filename)
				except URLGrabError as e:
					# Remove partly downloaded file.
					try:
						os.unlink(filename)
					except OSError:
						pass

					raise DownloadError("%s %s" % (os.path.basename(filename), e))

				# Check if the downloaded file was empty.
				if os.path.getsize(filename) == 0:
					# Remove the file and raise an error.
					os.unlink(filename)

					raise DownloadError(_("Downloaded empty file: %s") \
						% os.path.basename(filename))

			log.info("")

		return existant_files + download_files


class Mirror(object):
	def __init__(self, url, location=None, preferred=False):
		# Save URL of the mirror in full format
		self.url = url

		# Save the location (if given)
		self.location = location

		# Save preference
		self.preferred = False


class MirrorList(object):
	def __init__(self, pakfire, repo, mirrorlist):
		self.pakfire = pakfire
		self.repo = repo

		self.__mirrors = []

		# Save URL to more mirrors.
		self.mirrorlist = mirrorlist

	@property
	def base_mirror(self):
		if not self.repo.baseurl:
			return

		return Mirror(self.repo.baseurl, preferred=False)

	@property
	def distro(self):
		return self.repo.distro

	@property
	def cache(self):
		"""
			Shortcut to cache from repository.
		"""
		return self.repo.cache

	def update(self, force=False):
		# XXX should this be allowed?
		if not self.mirrorlist:
			return 

		# If the system is not online, we cannot download anything.
		if self.pakfire.offline:
			return

		log.debug("Updating mirrorlist for repository '%s' (force=%s)" % (self.repo.name, force))
		cache_filename = os.path.join("repodata", self.distro.sname, self.distro.release,
			self.repo.name, self.distro.arch, "mirrors")

		# Force the update if no mirrorlist is available.
		if not self.cache.exists(cache_filename):
			force = True

		if not force and self.cache.exists(cache_filename):
			age = self.cache.age(cache_filename)

			# If the age could be determined and is higher than 24h,
			# we force an update.
			if age and age > TIME_24H:
				force = True

		if force:
			g = MetadataDownloader(self.pakfire)

			try:
				mirrordata = g.urlread(self.mirrorlist, limit=MIRRORLIST_MAXSIZE)
			except URLGrabError as e:
				log.warning("Could not update the mirrorlist for repo '%s': %s" % (self.repo.name, e))
				return

			# XXX check for empty files or damaged output

			# Save new mirror data to cache.
			f = self.cache.open(cache_filename, "w")
			f.write(mirrordata)
			f.close()

		# Read mirrorlist from cache and parse it.
		self.forget_mirrors()
		with self.cache.open(cache_filename) as f:
			self.parse_mirrordata(f.read())

	def parse_mirrordata(self, data):
		data = json.loads(data)

		for mirror in data["mirrors"]:
			self.add_mirror(**mirror)

	def add_mirror(self, *args, **kwargs):
		mirror = Mirror(*args, **kwargs)

		self.__mirrors.append(mirror)

	def forget_mirrors(self):
		self.__mirrors = []

	@property
	def preferred(self):
		"""
			Return a generator for all mirrors that are preferred.
		"""
		for mirror in self.__mirrors:
			if mirror.preferred:
				yield mirror

	@property
	def non_preferred(self):
		"""
			Return a generator for all mirrors that are not preferred.
		"""
		for mirror in self.__mirrors:
			if not mirror.preferred:
				yield mirror

	@property
	def all(self):
		"""
			Return a generator for all mirrors.
		"""
		for mirror in self.__mirrors:
			yield mirror

	def group(self, grabber):
		"""
			Return a MirrorGroup object for the given grabber.
		"""
		# Make sure the mirrorlist is up to date.
		self.update()

		# A list of mirrors that is passed to MirrorGroup.
		mirrors = []

		# Add all preferred mirrors at the first place and shuffle them
		# that we will start at a random place.
		for mirror in self.preferred:
			mirrors.append({ "mirror" : mirror.url.encode("utf-8") })
		random.shuffle(mirrors)

		# All other mirrors are added as well and will only be used if all
		# preferred mirrors did not work.
		for mirror in self.all:
			mirror = { "mirror" : mirror.url.encode("utf-8") }
			if mirror in mirrors:
				continue

			mirrors.append(mirror)

		# Always add the base mirror if any.
		base_mirror = self.base_mirror
		if base_mirror:
			mirror = { "mirror" : base_mirror.url.encode("utf-8") }
			if not mirror in mirrors:
				mirrors.append(mirror)

		return MirrorGroup(grabber, mirrors)



class Downloader(object):
	def __init__(self, mirrors, files):
		self.grabber = PakfireGrabber()

		self.mirrorgroup = mirrors.group(self.grabber)


