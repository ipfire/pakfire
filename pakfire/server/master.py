#!/usr/bin/python

import logging
import hashlib
import os
import random
import shutil
import subprocess
import xmlrpclib

import pakfire
import pakfire.api
import pakfire.base

import pakfire.packages as packages
import pakfire.repository as repository
import pakfire.util as util
from pakfire.constants import *

from base import MasterSlave

class Source(object):
	def __init__(self, master, id, name, url, path, targetpath, revision, branch):
		self.master = master
		self.id = id
		self.name = name
		self.url = url
		self.targetpath = targetpath
		self.revision = revision
		self.branch = branch

		# If the repository is not yet checked out, we create a local clone
		# from it to work with it.
		if not os.path.exists(self.path):
			dirname = os.path.dirname(self.path)
			basename = os.path.basename(self.path)

			if not os.path.exists(dirname):
				os.makedirs(dirname)

			self._git("clone %s %s" % (self.url, basename), path=dirname)

		else:
			# Always refresh the repository to have the recent commits.
			self._git("fetch")

	@property
	def path(self):
		h = hashlib.sha1(self.url)

		# XXX path is to be changed
		return "/var/cache/pakfire/sources/%s" % h.hexdigest()

	@property
	def pakfire(self):
		return self.master.pakfire

	def _git(self, cmd, path=None):
		if not path:
			path = self.path

		cmd = "cd %s && git %s" % (path, cmd)

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

	def update_revision(self, (revision, merge), **pakfire_args):
		if not merge:
			self._git_checkout_revision(revision)

			# Get list of all changes files between the current revision and
			# the previous one.
			files = self._git_changed_files("HEAD^", "HEAD")

			self.update_files([f for f in files if f.endswith(".%s" % MAKEFILE_EXTENSION)],
				**pakfire_args)

		# Send update to the server.
		#self.master.update_revision(self, revision)

	def update_files(self, files, **pakfire_args):
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
		pakfire.api.dist(pkgs, resultdirs=[tmpdir,], **pakfire_args)

		# Create a kind of dummy repository to link the packages against it.
		repo = repository.LocalSourceRepository(self.pakfire,
			"source-%s" % rnd, "Source packages", tmpdir, idx="directory")
		repo.update(force=True)

		for pkg in repo.get_all():
			logging.debug("Processing package: %s" % pkg)

			# Register package in database and get an ID.
			pkg_id = self.master.package_add(self, pkg)

			# Upload the package.
			self.master.upload_package_file(self.id, pkg_id, pkg)

		util.rm(tmpdir)

	def update(self):
		# If there has been no data, yet we need to import all packages
		# that are currently checked out.
		if not self.revision:
			self.update_all()

		# Update the revisions on the server.
		for revision, merge in self._git_rev_list():
			if merge:
				continue

			logging.info("Sending revision to server: %s" % revision)
			self.master.conn.source_add_revision(self.id, revision)

		# Get all pending revisions from the server and process them.
		#for rev in self.master.conn.source_get_pending_revisions(self.id):
		#	self.update_revision(rev)

	def update_all(self):
		_files = []
		for dir, subdirs, files in os.walk(self.path):
			for f in files:
				if not f.endswith(".%s" % MAKEFILE_EXTENSION):
					continue

				_files.append(os.path.join(dir, f))

		self.update_files(_files)


class Master(MasterSlave):
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
