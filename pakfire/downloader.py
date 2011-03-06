#!/usr/bin/python

import json
import logging
import random

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.mirror import MirrorGroup
from urlgrabber.progress import TextMeter

from pakfire.constants import *

class PakfireGrabber(URLGrabber):
	"""
		Class to make some modifications on the urlgrabber configuration.
	"""
	# XXX add proxy, throttle things here

	def __init__(self, *args, **kwargs):
		kwargs.update({
			"quote" : 0,
			"user_agent" : "pakfire/%s" % PAKFIRE_VERSION,
		})

		URLGrabber.__init__(self, *args, **kwargs)


class PackageDownloader(PakfireGrabber):
	def __init__(self, *args, **kwargs):
		kwargs.update({
				"progress_obj" : TextMeter(),
		})

		PakfireGrabber.__init__(self, *args, **kwargs)


class MetadataDownloader(PakfireGrabber):
	def __init__(self, *args, **kwargs):
		kwargs.update({
			"http_headers" : (('Pragma', 'no-cache'),),
		})

		PakfireGrabber.__init__(self, *args, **kwargs)


class DatabaseDownloader(PackageDownloader):
	def __init__(self, *args, **kwargs):
		kwargs.update({
			"http_headers" : (('Pragma', 'no-cache'),),
		})

		PackageDownloader.__init__(self, *args, **kwargs)


class Mirror(object):
	def __init__(self, url, location=None, preferred=False):
		# Save URL of the mirror in full format
		self.url = url

		# Save the location (if given)
		self.location = location

		# Save preference
		self.preferred = False


class MirrorList(object):
	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

		self.__mirrors = []

		# Save URL to more mirrors.
		self.mirrorlist = repo.mirrorlist

		self.update(force=False)

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

		logging.debug("Updating mirrorlist for repository '%s' (force=%s)" % (self.repo.name, force))

		cache_filename = "mirrors/mirrorlist"

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
			g = MetadataDownloader()

			try:
				mirrordata = g.urlread(self.mirrorlist, limit=MIRRORLIST_MAXSIZE)
			except URLGrabError, e:
				logging.warning("Could not update the mirrorlist for repo '%s': %s" % (self.repo.name, e))
				return

			# XXX check for empty files or damaged output

			# Save new mirror data to cache.
			f = self.cache.open(cache_filename, "w")
			f.write(mirrordata)
			f.close()

		# Read mirrorlist from cache and parse it.
		with self.cache.open(cache_filename) as f:
			self.parse_mirrordata(f.read())

	def parse_mirrordata(self, data):
		data = json.loads(data)

		for mirror in data["mirrors"]:
			self.add_mirror(**mirror)

	def add_mirror(self, *args, **kwargs):
		mirror = Mirror(*args, **kwargs)

		self.__mirrors.append(mirror)

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
		# A list of mirrors that is passed to MirrorGroup.
		mirrors = []

		# Add all preferred mirrors at the first place and shuffle them
		# that we will start at a random place.
		for mirror in self.preferred:
			mirrors.append(mirror.url)
		random.shuffle(mirrors)

		# All other mirrors are added as well and will only be used if all
		# preferred mirrors did not work.
		for mirror in self.all:
			if mirror.url in mirrors:
				continue

			mirrors.append(mirror.url)

		return MirrorGroup(grabber, mirrors)



class Downloader(object):
	def __init__(self, mirrors, files):
		self.grabber = PakfireGrabber()

		self.mirrorgroup = mirrors.group(self.grabber)


