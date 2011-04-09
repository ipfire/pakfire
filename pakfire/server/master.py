#!/usr/bin/python

import logging
import os
import random
import shutil
import subprocess
import xmlrpclib

import pakfire
import pakfire.base

import pakfire.packages as packages
import pakfire.repository as repository
import pakfire.util as util
from pakfire.constants import *

class Source(object):
	def __init__(self, master, id, name, path, targetpath, revision, branch):
		self.master = master
		self.id = id
		self.name = name
		self.path = path
		self.targetpath = targetpath
		self.revision = revision
		self.branch = branch

	@property
	def pakfire(self):
		return self.master.pakfire

	def _git(self, cmd):
		cmd = "cd %s; git %s" % (self.path, cmd)

		logging.debug("Running command: %s" % cmd)

		return subprocess.check_output(["/bin/sh", "-c", cmd])

	def _git_rev_list(self, revision=None):
		if not revision:
			revision = self.revision

		command = "rev-list %s..origin/%s" % (revision, self.branch)

		# Get all normal commits.
		commits = self._git("%s --no-merges" % command)
		commits = commits.splitlines()

		revisions = []
		for commit in self._git(command).splitlines():
			# Check if commit is a normal commit or merge commit.
			merge = not commit in commits

			revisions.append((commit, merge))

		return reversed(revisions)

	def _git_changed_files(self, revision1, revision2=""):
		files = self._git("diff --name-only %s %s" % (revision1, revision2))

		return [os.path.join(self.path, f) for f in files.splitlines()]

	def _git_checkout_revision(self, revision):
		self._git("checkout %s" % revision)

	def update_revision(self, (revision, merge)):
		if not merge:
			self._git_checkout_revision(revision)

			# Get list of all changes files between the current revision and
			# the previous one.
			files = self._git_changed_files("HEAD^", "HEAD")

			self.update_files([f for f in files if f.endswith(".%s" % MAKEFILE_EXTENSION)])

		# Send update to the server.
		self.master.update_revision(self, revision)

	def update_files(self, files):
		rnd = random.randint(0, 1024**2)
		tmpdir = "/tmp/pakfire-source-%s" % rnd

		pkgs = []
		for file in files:
			if os.path.exists(file):
				pkgs.append(file)
			else:
				pkg_name = os.path.basename(os.path.dirname(file))

				# Send deleted package to server.
				self.master.package_remove(self, pkg_name)

		if not pkgs:
			return

		# XXX This totally ignores the local configuration.
		for pkg in pkgs:
			pakfire.dist(pkg, resultdirs=[tmpdir,])

		# Create a kind of dummy repository to link the packages against it.
		repo = repository.LocalSourceRepository(self.pakfire,
			"source-%s" % rnd, "Source packages", tmpdir, idx="directory")
		repo.update(force=True)

		for pkg in repo.get_all():
			logging.debug("Processing package: %s" % pkg)

			pkg_path = "%(name)s/%(epoch)s-%(version)s-%(release)s/%(arch)s" % pkg.info

			file = os.path.join(self.targetpath, pkg_path, os.path.basename(pkg.filename))
			dir  = os.path.dirname(file)

			print file

			if os.path.exists(file):
				logging.warning("Package does already exist: %s" % file)

			else:
				if not os.path.exists(dir):
					os.makedirs(dir)

				# Copy the source file to the designated data pool.
				shutil.copy2(pkg.filename, file)

			# Register package in database and get an ID.
			pkg_id = self.master.package_add(self, pkg)

			# Re-read the package metadata (mainly update filenames).
			pkg = packages.SourcePackage(self.pakfire, repo, file)

			self.master.package_file_add(self, pkg_id, pkg)

		util.rm(tmpdir)

	def update(self):
		# Update files from server.
		self._git("fetch")

		# If there has been no data, yet we need to import all packages
		# that are currently checked out.
		if not self.revision:
			self.update_all()

		for rev in self._git_rev_list():
			self.update_revision(rev)

	def update_all(self):
		_files = []
		for dir, subdirs, files in os.walk(self.path):
			for f in files:
				if not f.endswith(".%s" % MAKEFILE_EXTENSION):
					continue

				_files.append(os.path.join(dir, f))

		self.update_files(_files)


class Master(object):
	def __init__(self, **pakfire_args):
		self.pakfire = pakfire.base.Pakfire(**pakfire_args)

		server = self.pakfire.config._master.get("server")

		logging.info("Establishing RPC connection to: %s" % server)

		self.conn = xmlrpclib.Server(server)

	def update_sources(self):
		sources = self.conn.sources_get_all()

		for source in sources:
			source = Source(self, **source)

			source.update()

	def update_revision(self, source, revision):
		self.conn.sources_update_revision(source.id, revision)

	def package_add(self, source, pkg):
		logging.info("Adding package: %s" % pkg.friendly_name)

		# Collect data that is sent to the database...
		info = {
			"name"             : pkg.name,
			"epoch"            : pkg.epoch,
			"version"          : pkg.version,
			"release"          : pkg.release,
			"groups"           : " ".join(pkg.groups),
			"maintainer"       : pkg.maintainer,
			"license"          : pkg.license,
			"url"              : pkg.url,
			"summary"          : pkg.summary,
			"description"      : pkg.description,
			"supported_arches" : pkg.supported_arches,
			"source_id"        : source.id,
		}

		return self.conn.package_add(info)

	def package_file_add(self, source, pkg_id, pkg):
		logging.info("Adding package file: %s" % pkg.filename)

		info = {
			"path"        : pkg.filename[len(source.path) + 1:],
			"source_id"   : source.id,
			"type"        : pkg.type,
			"arch"        : pkg.arch,
			"summary"     : pkg.summary,
			"description" : pkg.description,
			"requires"    : " ".join(pkg.requires),
			"provides"    : "",
			"obsoletes"   : "",
			"conflicts"   : "",
			"url"         : pkg.url,
			"license"     : pkg.license,
			"maintainer"  : pkg.maintainer,
			"size"        : pkg.size,
			"hash1"       : pkg.hash1,
			"build_host"  : pkg.build_host,
			"build_id"    : pkg.build_id,
			"build_time"  : pkg.build_time,
			"uuid"        : pkg.uuid,
		}

		if isinstance(pkg, packages.BinaryPackage):
			info.update({
				"provides"    : " ".join(pkg.provides),
				"obsoletes"   : " ".join(pkg.obsoletes),
				"conflicts"   : " ".join(pkg.conflicts),
			})

		return self.conn.package_file_add(pkg_id, info)

	def package_remove(self, source, pkg):
		logging.info("Package '%s' has been removed." % pkg)

