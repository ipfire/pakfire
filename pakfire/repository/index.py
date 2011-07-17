#!/usr/bin/python

import logging
import os

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

	def update(self, force=False):
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

	def create_relation(self, *args, **kwargs):
		return self.pakfire.create_relation(*args, **kwargs)

	def add_package(self, pkg):
		# XXX Skip packages without a UUID
		#if not pkg.uuid:
		#	logging.warning("Skipping package which lacks UUID: %s" % pkg)
		#	return
		if not pkg.build_time:
			return

		logging.debug("Adding package to index %s: %s" % (self, pkg))

		solvable = satsolver.Solvable(self.solver_repo, pkg.name,
			pkg.friendly_version, pkg.arch)

		# Save metadata.
		solvable.set_vendor(pkg.vendor)
		solvable.set_hash1(pkg.hash1)
		solvable.set_uuid(pkg.uuid)
		solvable.set_maintainer(pkg.maintainer)
		solvable.set_groups(" ".join(pkg.groups))

		# Save upstream information (summary, description, license, url).
		solvable.set_summary(pkg.summary)
		solvable.set_description(pkg.description)
		solvable.set_license(pkg.license)
		solvable.set_url(pkg.url)

		# Save build information.
		solvable.set_buildhost(pkg.build_host)
		solvable.set_buildtime(pkg.build_time)

		# Save filename.
		filename = os.path.basename(pkg.filename)
		solvable.set_filename(filename)
		solvable.set_downloadsize(pkg.size)
		solvable.set_installsize(pkg.inst_size)

		# Import all requires.
		for req in pkg.requires:
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


class IndexSolv(Index):
	def check(self):
		pass # XXX to be done

	def update(self, force=False):
		self._update_metadata(force)
		self._update_database(force)

	def _update_metadata(self, force):
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
					logging.debug("Metadata is recent enough. I don't download it again.")

				# Open old metadata for comparison.
				old_metadata = metadata.Metadata(self.pakfire, self,
					self.cache.abspath(filename))

		if download:
			logging.debug("Going to (re-)download the repository metadata.")

			# Initialize a grabber for download.
			grabber = downloader.MetadataDownloader()
			grabber = self.repo.mirrors.group(grabber)

			data = grabber.urlread(filename, limit=METADATA_DOWNLOAD_LIMIT)

			# Parse new metadata for comparison.
			new_metadata = metadata.Metadata(self.pakfire, self, metadata=data)

			if old_metadata and new_metadata < old_metadata:
				logging.warning("The downloaded metadata was less recent than the current one. Trashing that.")

			else:
				# We explicitely rewrite the metadata if it is equal to have
				# a new timestamp and do not download it over and over again.
				with self.cache.open(filename, "w") as o:
					o.write(data)

		# Parse the metadata that we just downloaded or load it from cache.
		self.metadata = metadata.Metadata(self.pakfire, self,
			self.cache.abspath(filename))

	def _update_database(self, force):
		# Construct cache and download filename.
		filename = os.path.join(METADATA_DOWNLOAD_PATH, self.metadata.database)

		if not self.cache.exists(filename):
			# Initialize a grabber for download.
			grabber = downloader.DatabaseDownloader(
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
	def check(self):
		pass # XXX to be done

	@property
	def path(self):
		path = self.repo.path

		if path.startswith("file://"):
			path = path[7:]

		return path

	def update(self, force=False):
		logging.debug("Updating repository index '%s' (force=%s)" % (self.path, force))

		# Do nothing if the update is not forced but populate the database
		# if no packages are present.
		if not force and len(self.repo):
			return

		# Collect all packages from default path.
		self.collect_packages(self.path)

	def collect_packages(self, path):
		# XXX make progress bar for that
		for dir, subdirs, files in os.walk(path):
			for file in sorted(files):
				# Skip files that do not have the right extension
				if not file.endswith(".%s" % PACKAGE_EXTENSION):
					continue

				package = packages.open(self.pakfire, self.repo, os.path.join(dir, file))

				if isinstance(package, packages.BinaryPackage):
					if not package.arch in (self.repo.arch, "noarch"):
						logging.warning("Skipped package with wrong architecture: %s (%s)" \
							% (package.filename, package.arch))
						print package.type
						continue

				# Skip all source packages.
				elif isinstance(package, packages.SourcePackage):
					continue

				self.add_package(package)

				yield package


class IndexLocal(Index):
	def init(self):
		self.db = database.DatabaseLocal(self.pakfire, self.repo)

	def check(self):
		# XXX Create the database and lock it or something.
		pass

	def update(self, force=True):
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

				# XXX currently broken
				#self.add_package(pkg)

			if pb:
				pb.finish()
