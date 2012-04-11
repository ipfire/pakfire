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
import stat
import time

import pakfire.util as util
from pakfire.constants import *

class RepositoryCache(object):
	"""
		An object that is able to cache all data that is loaded from a
		remote repository.
	"""
	path = REPO_CACHE_DIR

	def __init__(self, pakfire, repo):
		self.pakfire = pakfire
		self.repo = repo

		self.__created = None

	@property
	def created(self):
		"""
			Tells us, if the cache was already created.
		"""
		if self.__created is None:
			self.__created = os.path.exists(self.path)

		return self.__created

	def abspath(self, path, create=True):
		if create:
			self.create()

		return os.path.join(self.path, path)

	def create(self):
		"""
			Create all necessary directories.
		"""
		# Do nothing, if the cache has already been created.
		if self.created:
			return

		if not os.path.exists(self.path):
			os.makedirs(self.path)

		self.__created = True

	def exists(self, filename):
		"""
			Returns True if a file exists and False if it doesn't.
		"""
		return os.path.exists(self.abspath(filename))

	def age(self, filename):
		"""
			Returns the age of a downloaded file in minutes.
			i.e. the time from download until now.
		"""
		if not self.exists(filename):
			return None

		filename = self.abspath(filename)

		# Creation time of the file
		ctime = os.stat(filename)[stat.ST_CTIME]

		return (time.time() - ctime) / 60

	def open(self, filename, *args, **kwargs):
		filename = self.abspath(filename)

		# Create directory if not existant.
		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		return open(filename, *args, **kwargs)

	def hash1(self, filename):
		"""
			Return hash of the file in the cache.
		"""
		return util.calc_hash1(self.abspath(filename))

	def verify(self, filename, hash1):
		"""
			Return a bool that indicates if a file matches the given hash.
		"""
		return self.hash1(filename) == hash1

	def remove(self, filename):
		"""
			Remove a file from cache.
		"""
		if not self.exists(filename):
			return

		filename = self.abspath(filename)
		os.unlink(filename)

	def destroy(self):
		"""
			Remove all files from this cache.
		"""
		if self.created:
			util.rm(self.path)
