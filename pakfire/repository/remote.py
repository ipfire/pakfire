#!/usr/bin/python

import logging
import os

import cache
import index

import pakfire.downloader as downloader

from base import RepositoryFactory

class RemoteRepository(RepositoryFactory):
	def __init__(self, pakfire, name, description, url, mirrorlist, gpgkey, enabled):
		RepositoryFactory.__init__(self, pakfire, name, description)

		# Parse arguments.
		self.url = url
		self.gpgkey = gpgkey
		self.mirrorlist = mirrorlist

		if enabled:
			self.enabled = True
		else:
			self.enabled = False

		# Create a cache for the repository where we can keep all temporary data.
		self.cache = cache.RepositoryCache(self.pakfire, self)

		# Initialize mirror servers.
		self.mirrors = downloader.MirrorList(self.pakfire, self)

		# Initialize index.
		self.index = index.RemoteIndex(self.pakfire, self)

		logging.debug("Created new repository(name='%s', url='%s', enabled='%s')" % \
			(self.name, self.url, self.enabled))

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.url)

	@property
	def local(self):
		# If files are located somewhere in the filesystem we assume it is
		# local.
		if self.url.startswith("file://"):
			return True

		# Otherwise not.
		return False

	@property
	def arch(self):
		return self.pakfire.distro.arch

	@property
	def path(self):
		if self.local:
			return self.url[7:]

		return self.cache.path

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

	def update(self, force=False, offline=False):
		if self.index:
			self.index.update(force=force, offline=offline)

	def _replace_from_cache(self, pkg):
		for _pkg in self.cache.packages:
			if pkg == _pkg:
				pkg = _pkg
				break

		return pkg

	@property
	def packages(self):
		for pkg in self.index.packages:
			yield self._replace_from_cache(pkg)

	def get_by_provides(self, requires):
		for pkg in self.index.get_by_provides(requires):
			yield self._replace_from_cache(pkg)

	def get_by_file(self, filename):
		return self.index.get_by_file(filename)
