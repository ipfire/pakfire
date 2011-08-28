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
import re

import base
import file

class SolvPackage(base.Package):
	def __init__(self, pakfire, solvable, repo=None):
		base.Package.__init__(self, pakfire, repo)

		# Save solvable object
		self.solvable = solvable

		self.__evr = None

	@property
	def uuid(self):
		return self.solvable.get_uuid()

	@property
	def hash1(self):
		return self.solvable.get_hash1()

	@property
	def name(self):
		return self.solvable.get_name()

	@property
	def evr(self):
		if self.__evr is None:
			m = re.match("^([0-9]+\:)?([0-9A-Za-z\.\-_]+)-([0-9]+\.?[a-z0-9]+|[0-9]+)$",
				self.solvable.get_evr())

			if m:
				(e, v, r) = m.groups()

				if e:
					e = e.replace(":", "")
					e = int(e)

				self.__evr = (e, v, r)

		assert self.__evr
		return self.__evr

	@property
	def epoch(self):
		return self.evr[0]

	@property
	def version(self):
		return self.evr[1]

	@property
	def release(self):
		return self.evr[2]

	@property
	def arch(self):
		return self.solvable.get_arch()

	@property
	def repo(self):
		if self._repo:
			return self._repo

		repo_name = self.solvable.get_repo_name()
		return self.pakfire.repos.get_repo(repo_name)

	@property
	def summary(self):
		return self.solvable.get_summary()

	@property
	def description(self):
		return self.solvable.get_description() or ""

	@property
	def groups(self):
		groups = self.solvable.get_groups()

		if groups:
			return groups.split()

		return []

	@property
	def license(self):
		return self.solvable.get_license()

	@property
	def maintainer(self):
		return self.solvable.get_maintainer()

	@property
	def url(self):
		return self.solvable.get_url()

	@property
	def size(self):
		return self.solvable.get_downloadsize()

	@property
	def uuid(self):
		return self.solvable.get_uuid()

	@property
	def build_host(self):
		return self.solvable.get_buildhost()

	@property
	def build_time(self):
		return self.solvable.get_buildtime()

	@property
	def build_id(self):
		return "XXX CURRENTLY NOT IMPLEMENTED"

	@property
	def provides(self):
		return self.solvable.get_provides()

	@property
	def _requires(self):
		requires = self.solvable.get_requires()

		try:
			i = requires.index("solvable:prereqmarker")

			return (requires[:i], requires[i:],)
		except ValueError:
			return ([], requires,)

	@property
	def prerequires(self):
		prereqs, reqs = self._requires

		return prereqs

	@property
	def requires(self):
		prereqs, reqs = self._requires

		return reqs

	@property
	def obsoletes(self):
		return self.solvable.get_obsoletes()

	@property
	def conflicts(self):
		return self.solvable.get_conflicts()

	@property
	def filename(self):
		return self.solvable.get_filename()

	@property
	def filelist(self):
		# XXX need to support filelist.
		return ["%s does not support filelists, yet." % self.__class__.__name__,]

	@property
	def is_in_cache(self):
		# Local files are always kinda cached.
		if self.repo.local:
			return True

		return self.repo.cache.exists("package/%s" % self.filename)

	def get_from_cache(self):
		path = None

		if self.repo.local:
			# Search for a file in the local repository. It can be either in
			# the root directory of the repository or in a subdirectory that
			# is named by the architecture.
			for i in ("", self.arch,):
				path = os.path.join(self.repo.path, i, self.filename)

				if os.path.exists(path):
					return file.BinaryPackage(self.pakfire, self.repo, path)
		else:
			filename = "packages/%s" % self.filename

			if self.repo.cache.exists(filename):
				path = self.repo.cache.abspath(filename)

		if path:
			return file.BinaryPackage(self.pakfire, self.repo, path)

	def download(self, text=""):
		if not self.repo.local:
			self.repo.download(self, text=text)

		return self.get_from_cache()

	def get_scriptlet(self, type):
		# XXX TODO
		return None
