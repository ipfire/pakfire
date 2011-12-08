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

import database
import metadata

import pakfire.compress as compress
import pakfire.downloader as downloader
import pakfire.packages as packages
import pakfire.satsolver as satsolver
import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class Index(object):
	def __init__(self, pakfire, repo):
		self.pakfire = pakfire

		# Create reference to repository and the solver repo.
		self.repo = repo
		self.solver_repo = repo.solver_repo

		self.init()

		# Check, if initialization was okay.
		self.check()

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.repo)

	def __len(self):
		return len(self.repo)

	@property
	def cache(self):
		return self.repo.cache

	def init(self):
		pass

	def check(self):
		"""
			Check if everything was correctly initialized.
		"""
		raise NotImplementedError

	def update(self, force=False, offline=False):
		raise NotImplementedError

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

	def commit(self):
		"""
			Commit index data to disk.
		"""
		pass

	def create_relation(self, *args, **kwargs):
		return self.pakfire.create_relation(*args, **kwargs)

	def add_package(self, pkg):
		# XXX Skip packages without a UUID
		#if not pkg.uuid:
		#	log.warning("Skipping package which lacks UUID: %s" % pkg)
		#	return
		if not pkg.build_time:
			return

		log.debug("Adding package to index %s: %s" % (self, pkg))

		solvable = satsolver.Solvable(self.solver_repo, pkg.name,
			pkg.friendly_version, pkg.arch)

		# Save metadata.
		if pkg.vendor:
			solvable.set_vendor(pkg.vendor)

		hash1 = pkg.hash1
		assert hash1
		solvable.set_hash1(hash1)

		assert pkg.uuid
		solvable.set_uuid(pkg.uuid)

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
			rel = self.create_relation(req)
			solvable.add_requires(rel)

		# Import all provides.
		for prov in pkg.provides:
			rel = self.create_relation(prov)
			solvable.add_provides(rel)

		# Import all conflicts.
		for conf in pkg.conflicts:
			rel = self.create_relation(conf)
			solvable.add_conflicts(rel)

		# Import all obsoletes.
		for obso in pkg.obsoletes:
			rel = self.create_relation(obso)
			solvable.add_obsoletes(rel)

		# Import all files that are in the package.
		rel = self.create_relation("solvable:filemarker")
		solvable.add_provides(rel)
		for file in pkg.filelist:
			rel = self.create_relation(file)
			solvable.add_provides(rel)

	def rem_package(self, pkg):
		# XXX delete the solvable from the index.
		self.db.rem_package(pkg)

	def clear(self):
		"""
			Forget all packages from memory.
		"""
		self.solver_repo.clear()


class IndexSolv(Index):
	def check(self):
		pass # XXX to be done

	def update(self, force=False, offline=False):
		self._update_metadata(force, offline)
		self._update_database(force, offline)

	def _update_metadata(self, force, offline=False):
		filename = os.path.join(METADATA_DOWNLOAD_PATH, METADATA_DOWNLOAD_FILE)

		# Marker if we need to do the download.
		download = True

		# Marker for the current metadata.
		old_metadata = None

		if not force:
			# Check if file does exists and is not too old.
			if self.cache.exists(filename):
				age = self.cache.age(filename)
				if age and age < TIME_10M:
					download = False
					log.debug("Metadata is recent enough. I don't download it again.")

				# Open old metadata for comparison.
				old_metadata = metadata.Metadata(self.pakfire, self,
					self.cache.abspath(filename))

			# If no metadata was downloaded and we are in offline mode.
			elif offline:
				# If we cannot download new metadata, we should skip this
				# repository.
				return

				#raise OfflineModeError, _("There is no metadata for the repository '%s' and"
				#	" we cannot download any because we are running in offline mode."
				#	" Connect to a network or disable this repository.") % self.repo.name

		elif force and offline:
			raise OfflineModeError, _("I cannot be forced to re-download the metadata for"
				" the repository '%s' when running in offline mode.") % self.repo.name

		if download:
			# We are supposed to download new metadata, but we are running in
			# offline mode. That's okay. Just doing nothing.
			if not offline:
				log.debug("Going to (re-)download the repository metadata.")

				# Initialize a grabber for download.
				grabber = downloader.MetadataDownloader(self.pakfire)
				grabber = self.repo.mirrors.group(grabber)

				data = grabber.urlread(filename, limit=METADATA_DOWNLOAD_LIMIT)

				# Parse new metadata for comparison.
				new_metadata = metadata.Metadata(self.pakfire, self, metadata=data)

				if old_metadata and new_metadata < old_metadata:
					log.warning("The downloaded metadata was less recent than the current one. Trashing that.")

				else:
					# We explicitely rewrite the metadata if it is equal to have
					# a new timestamp and do not download it over and over again.
					with self.cache.open(filename, "w") as o:
						o.write(data)

		# Parse the metadata that we just downloaded or load it from cache.
		self.metadata = metadata.Metadata(self.pakfire, self,
			self.cache.abspath(filename))

	def _update_database(self, force, offline=False):
		if not hasattr(self, "metadata"):
			return

		# Construct cache and download filename.
		filename = os.path.join(METADATA_DOWNLOAD_PATH, self.metadata.database)

		if not self.cache.exists(filename):
			if offline:
				# If there is not database and we are in offline mode, we cannot
				# download anything so we just skip the rest of this function.
				return

				#raise OfflineModeError, _("Your repository metadata is outdated "
				#	" and a new version needs to be downloaded.")

			# Initialize a grabber for download.
			grabber = downloader.DatabaseDownloader(
				self.pakfire,
				text = _("%s: package database") % self.repo.name,
			)
			grabber = self.repo.mirrors.group(grabber)

			data = grabber.urlread(filename)

			with self.cache.open(filename, "w") as o:
				o.write(data)

			# decompress the database
			if self.metadata.database_compression:
				# Open input file and remove the file immediately.
				# The fileobj is still open and the data will be removed
				# when it is closed.
				compress.decompress(self.cache.abspath(filename),
					algo=self.metadata.database_compression)

			# check the hashsum of the downloaded file
			if not util.calc_hash1(self.cache.abspath(filename)) == self.metadata.database_hash1:
				# XXX an exception is not a very good idea because this file could
				# be downloaded from another mirror. need a better way to handle this.

				# Remove bad file from cache.
				self.cache.remove(filename)

				raise Exception, "Downloaded file did not match the hashsum. Need to re-download it."

		# (Re-)open the database.
		self.read(self.cache.abspath(filename))


class IndexDir(Index):
	def init(self):
		self.pkg_type = None

		if self.repo.type == "binary":
			self.pkg_type = packages.BinaryPackage
		elif self.repo.type == "source":
			self.pkg_type = packages.SourcePackage

		assert self.pkg_type

	def check(self):
		pass # XXX to be done

	@property
	def path(self):
		path = self.repo.path

		if path.startswith("file://"):
			path = path[7:]

		return path

	def update(self, force=False, offline=False):
		log.debug("Updating repository index '%s' (force=%s)" % (self.path, force))

		# Do nothing if the update is not forced but populate the database
		# if no packages are present.
		if not force and len(self.repo):
			return

		# Collect all packages from default path.
		self.collect_packages(self.path)

	def collect_packages(self, path):
		log.debug("Collecting all packages from %s" % path)
		pkgs = []

		# Get a filelist of all files that could possibly be packages.
		files = []

		if os.path.isdir(path):
			for dir, subdirs, _files in os.walk(path):
				for file in sorted(_files):
					# Skip files that do not have the right extension
					if not file.endswith(".%s" % PACKAGE_EXTENSION):
						continue

					file = os.path.join(dir, file)
					files.append(file)
		elif os.path.isfile(path) and path.endswith(".%s" % PACKAGE_EXTENSION):
			files.append(path)

		if not files:
			return pkgs

		# Create progress bar.
		pb = util.make_progress(_("Loading from %s") % path, len(files))
		i = 0

		for file in files:
				if pb:
					i += 1
					pb.update(i)

				package = packages.open(self.pakfire, self.repo, file)

				# Find all packages with the given type and skip those of
				# the other type.
				if not isinstance(package, self.pkg_type):
					continue

				self.add_package(package)
				pkgs.append(package)

		if pb:
			pb.finish()

		# Internalize the repository, that all imported information
		# is available for access.
		self.solver_repo.internalize()

		return pkgs


class IndexLocal(Index):
	def init(self):
		self.db = database.DatabaseLocal(self.pakfire, self.repo)

		# Read SOLV cache file.
		filename = os.path.join(self.pakfire.path, PACKAGES_SOLV)
		if os.path.exists(filename):
			self.read(filename)

	def commit(self):
		# Write SOLV cache file.
		filename = os.path.join(self.pakfire.path, PACKAGES_SOLV)

		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		self.write(filename)

	def check(self):
		# XXX Create the database and lock it or something.
		pass

	def update(self, force=True, offline=False):
		if self.solver_repo.size() == 0:
			force = True

		if force:
			package_count = len(self.db)

			# Nothing to do here, if there are no packages in the database.
			if not package_count:
				return

			# Add all packages from the database to the index.
			pb = util.make_progress(_("Loading installed packages"), package_count)

			i = 0
			for pkg in self.db.packages:
				if pb:
					i += 1
					pb.update(i)

				self.add_package(pkg)

			if pb:
				pb.finish()

	@property
	def filelist(self):
		for pkg in self.db.packages:
			for file in pkg.filelist:
				yield file
