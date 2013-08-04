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

import pakfire.packages as packages
import pakfire.satsolver as satsolver

class Index(object):
	"""
		Wraps around the solvable index in the memory.
	"""

	def __init__(self, pakfire, repo):
		self.pakfire = pakfire

		# Create reference to repository and the solver repo.
		self.repo = repo
		self.solver_repo = repo.solver_repo

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.repo)

	def __del__(self):
		self.clear()

	def read(self, filename):
		"""
			Read file in SOLV format from filename.
		"""
		self.solver_repo.read(filename)

	def write(self, filename):
		"""
			Write content to filename in SOLV format.
		"""
		self.solver_repo.write(filename)

	def optimize(self):
		"""
			Optimize the index.
		"""
		self.solver_repo.internalize()

	def add_package(self, pkg):
		log.debug("Adding package to index %s: %s" % (self, pkg))

		solvable = satsolver.Solvable(self.solver_repo, pkg.name,
			pkg.friendly_version, pkg.arch)

		assert pkg.uuid
		solvable.set_uuid(pkg.uuid)

		hash1 = pkg.hash1
		assert hash1
		solvable.set_hash1(hash1)

		# Save metadata.
		if pkg.vendor:
			solvable.set_vendor(pkg.vendor)

		if pkg.maintainer:
			solvable.set_maintainer(pkg.maintainer)

		if pkg.groups:
			solvable.set_groups(" ".join(pkg.groups))

		# Save upstream information (summary, description, license, url).
		if pkg.summary:
			solvable.set_summary(pkg.summary)

		if pkg.description:
			solvable.set_description(pkg.description)

		if pkg.license:
			solvable.set_license(pkg.license)

		if pkg.url:
			solvable.set_url(pkg.url)

		# Save build information.
		if pkg.build_host:
			solvable.set_buildhost(pkg.build_host)

		if pkg.build_time:
			solvable.set_buildtime(pkg.build_time)

		# Save filename.
		filename = os.path.basename(pkg.filename)
		assert filename
		solvable.set_filename(filename)

		solvable.set_downloadsize(pkg.size)
		solvable.set_installsize(pkg.inst_size)

		# Import all requires.
		requires = pkg.requires
		prerequires = pkg.prerequires
		if prerequires:
			requires.append("solvable:prereqmarker")
			requires += prerequires

		for req in requires:
			rel = self.pakfire.pool.create_relation(req)
			solvable.add_requires(rel)

		# Import all provides.
		for prov in pkg.provides:
			rel = self.pakfire.pool.create_relation(prov)
			solvable.add_provides(rel)

		# Import all conflicts.
		for conf in pkg.conflicts:
			rel = self.pakfire.pool.create_relation(conf)
			solvable.add_conflicts(rel)

		# Import all obsoletes.
		for obso in pkg.obsoletes:
			rel = self.pakfire.pool.create_relation(obso)
			solvable.add_obsoletes(rel)

		# Import all files that are in the package.
		rel = self.pakfire.pool.create_relation("solvable:filemarker")
		solvable.add_provides(rel)
		for file in pkg.filelist:
			rel = self.pakfire.pool.create_relation(file)
			solvable.add_provides(rel)

		# Import all recommends.
		for reco in pkg.recommends:
			rel = self.pakfire.pool.create_relation(reco)
			solvable.add_recommends(rel)

		# Import all suggests.
		for sugg in pkg.suggests:
			rel = self.pakfire.pool.create_relation(sugg)
			solvable.add_suggests(rel)

	def clear(self):
		"""
			Forget all packages from memory.
		"""
		self.solver_repo.clear()
