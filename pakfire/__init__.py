#!/usr/bin/python

import logging
import os
import random
import string

import builder
import config
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

__version__ = PAKFIRE_VERSION


class Pakfire(object):
	def __init__(self, path="/", builder=False, configs=[],
			disable_repos=None):
		# Check if we are operating as the root user.
		self.check_root_user()

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
		self.repos.update()

	def check_root_user(self):
		if not os.getuid() == 0 or not os.getgid() == 0:
			raise Exception, "You must run pakfire as the root user."

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

	def build(self, pkg, arch=None, resultdirs=None):
		self.check_build_mode()
		self.check_host_arch(arch)

		if not resultdirs:
			resultdirs = []

		# Always include local repository
		resultdirs.append(self.repos.local_build.path)

		b = builder.Builder(pakfire=self, pkg=pkg)

		try:
			b.prepare()
			b.extract()
			b.build()
			b.install_test()

			# Copy-out all resultfiles
			for resultdir in resultdirs:
				if not resultdir:
					continue

				b.copy_result(resultdir)

		except BuildError:
			b.shell()

		finally:
			b.destroy()

	def shell(self, pkg, arch=None):
		self.check_build_mode()
		self.check_host_arch(arch)

		b = builder.Builder(pakfire=self, pkg=pkg)

		try:
			b.prepare()
			b.extract()
			b.shell()
		finally:
			b.destroy()

	def dist(self, pkgs, resultdirs=None):
		self.check_build_mode()

		# Select first package out of pkgs.
		pkg = pkgs[0]

		b = builder.Builder(pakfire=self, pkg=pkg)
		try:
			b.prepare()
			b.extract(build_deps=False)
		except:
			# If there is any exception, we destroy our stuff and raise it.
			b.destroy()
			raise

		if not resultdirs:
			resultdirs = []

		# Always include local repository
		resultdirs.append(self.repos.local_build.path)

		try:
			for pkg in pkgs:
				# Change package of the builder to current one.
				b.pkg = pkg
				b.extract(build_deps=False)

				# Run the actual dist.
				b.dist()

				# Copy-out all resultfiles
				for resultdir in resultdirs:
					if not resultdir:
						continue

					b.copy_result(resultdir)

				# Cleanup all the stuff from pkg.
				b.cleanup()
		finally:
			b.destroy()

	def install(self, requires):
		ds = depsolve.DependencySet(pakfire=self)

		for req in requires:
			if isinstance(req, packages.BinaryPackage):
				ds.add_package(req)
			else:
				ds.add_requires(req)

		ds.resolve()
		ds.dump()

		ret = cli.ask_user(_("Is this okay?"))
		if not ret:
			return

		ts = transaction.Transaction(self, ds)
		ts.run()

	def update(self, pkgs):
		ds = depsolve.DependencySet(pakfire=self)

		for pkg in ds.packages:
			# Skip unwanted packages (passed on command line)
			if pkgs and not pkg.name in pkgs:
				continue

			updates = self.repos.get_by_name(pkg.name)
			updates = packages.PackageListing(updates)

			latest = updates.get_most_recent()

			# If the current package is already the latest
			# we skip it.
			if latest == pkg:
				continue

			# Otherwise we want to update the package.
			ds.add_package(latest)

		ds.resolve()
		ds.dump()

		ret = cli.ask_user(_("Is this okay?"))
		if not ret:
			return

		ts = transaction.Transaction(self, ds)
		ts.run()

	def provides(self, patterns):
		pkgs = []

		for pattern in patterns:
			requires = depsolve.Requires(None, pattern)
			pkgs += self.repos.get_by_provides(requires)

		pkgs = packages.PackageListing(pkgs)
		#pkgs.unique()

		return pkgs

	def repo_create(self, path, input_paths):
		repo = repository.LocalRepository(
			self,
			name="new",
			description="New repository.",
			path=path,
		)

		for input_path in input_paths:
			repo._collect_packages(input_path)

		repo.save()

	def grouplist(self, group):
		pkgs = self.repos.get_by_group(group)

		pkgs = packages.PackageListing(pkgs)
		pkgs.unique()

		return [p.name for p in pkgs]
