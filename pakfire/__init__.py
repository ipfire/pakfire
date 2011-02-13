#!/usr/bin/python

import logging
import os
import random
import string

import builder
import config
import database
import depsolve
import distro
import logger
import packages
import plugins
import repository
import transaction

from constants import *
from errors import BuildError, PakfireError
from i18n import _

__version__ = 0.1


class Pakfire(object):
	def __init__(self, path="/tmp/pakfire", builder=False, configs=[],
			disable_repos=None):
		# The path where we are operating in
		self.path = path

		# Save if we are in the builder mode
		self.builder = builder

		if self.builder:
			rnd = random.sample(string.lowercase + string.digits, 12)
			self.path = os.path.join(BUILD_ROOT, "".join(rnd))

		self.debug = False

		# Read configuration file(s)
		self.config = config.Config(pakfire=self)
		for filename in configs:
			self.config.read(filename)

		# Setup the logger
		logger.setup_logging(self.config)
		self.config.dump()

		# Load plugins
		self.plugins = plugins.Plugins(pakfire=self)

		# Get more information about the distribution we are running
		# or building
		self.distro = distro.Distribution(pakfire=self)

		# Load all repositories
		self.repos = repository.Repositories(pakfire=self)

		# Run plugins that implement an initialization method.
		self.plugins.run("init")

		# Disable repositories if passed on command line
		if disable_repos:
			for repo in disable_repos:
				self.repos.disable_repo(repo)

		# Check if there is at least one enabled repository.
		if len(self.repos) < 2:
			raise PakfireError, "No repositories were configured."

		# Update all indexes of the repositories (not force) so that we will
		# always work with valid data.
		self.repos.update_indexes()

	def check_build_mode(self):
		"""
			Check if we are running in build mode.
			Otherwise, raise an exception.
		"""
		if not self.builder:
			raise BuildError, "Cannot build when not in build mode."

	def check_host_arch(self, arch):
		"""
			Check if we can build for arch.
		"""

		# If no arch was given on the command line we build for our
		# own arch which should always work.
		if not arch:
			return True

		if not self.distro.host_supports_arch(arch):
			raise BuildError, "Cannot build for the target architecture: %s" % arch

		raise BuildError, arch

	def build(self, pkg, arch=None, resultdir=None):
		self.check_build_mode()
		self.check_host_arch(arch)

		b = builder.Builder(pakfire=self, pkg=pkg)
		b.extract()

		if not resultdir:
			resultdir = self.config.get("resultdir")

		try:
			b.build()
			b.copy_result(resultdir)
		finally:
			b.cleanup()

	def shell(self, pkg, arch=None):
		self.check_build_mode()
		self.check_host_arch(arch)

		b = builder.Builder(pakfire=self, pkg=pkg)
		b.extract(SHELL_PACKAGES)

		try:
			b.shell()
		finally:
			b.cleanup()

	def dist(self, pkg, resultdir=None):
		self.check_build_mode()

		b = builder.Builder(pakfire=self, pkg=pkg)
		b.extract(build_deps=False)

		if not resultdir:
			resultdir = self.config.get("resultdir")

		try:
			b.dist()
			b.copy_result(resultdir)
		finally:
			b.cleanup()

	def install(self, requires):
		ds = depsolve.DependencySet(pakfire=self)

		for req in requires:
			if isinstance(req, packages.BinaryPackage):
				ds.add_package(req)
			else:
				ds.add_requires(req)

		ds.resolve()

		ts = transaction.TransactionSet(self, ds)
		ts.dump()

		ret = cli.ask_user(_("Is this okay?"))
		if not ret:
			return

		ts.run()

	def provides(self, patterns):
		pkgs = []

		for pattern in patterns:
			pkgs += self.repos.get_by_provides(pattern)

		pkgs = packages.PackageListing(pkgs)
		#pkgs.unique()

		return pkgs

	def repo_create(self, path):
		if not os.path.exists(path) or not os.path.isdir(path):
			raise PakfireError, "Given path is not existant or not a directory: %s" % path

		repo = repository.RemoteRepository(
			self,
			name="new",
			description="New repository.",
			url="file://%s" % path,
			gpgkey="XXX",
			enabled=True,
		)

		repo.save_index()

