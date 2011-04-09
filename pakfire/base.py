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
import repository
import transaction
import util

from constants import *
from i18n import _

class Pakfire(object):
	def __init__(self, builder=False, configs=[], disable_repos=None,
			distro_config=None):
		# Check if we are operating as the root user.
		self.check_root_user()

		# The path where we are operating in.
		if builder:
			self.builder = True
			self.path = os.path.join(BUILD_ROOT, util.random_string())
		else:
			self.builder = False
			self.path = "/"

			# XXX check if we are actually running on an ipfire system.

		# Read configuration file(s)
		self.config = config.Config(pakfire=self)
		for filename in configs:
			self.config.read(filename)

		# Setup the logger
		logger.setup_logging(self.config)
		self.config.dump()

		# Get more information about the distribution we are running
		# or building
		self.distro = distro.Distribution(self, distro_config)
		self.repos  = repository.Repositories(self)

		# Disable repositories if passed on command line
		if disable_repos:
			for repo in disable_repos:
				self.repos.disable_repo(repo)

		# Update all indexes of the repositories (not force) so that we will
		# always work with valid data.
		self.repos.update()

	def destroy(self):
		if not self.path == "/":
			util.rm(self.path)

	@property
	def supported_arches(self):
		return self.distro.supported_arches

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

	def info(self):
		pkgs = []

		for pattern in patterns:
			pkgs += self.repos.get_by_glob(pattern)

		return packages.PackageListing(pkgs)

	def search(self, pattern):
		# Do the search.
		pkgs = self.repos.search(pattern)

		# Return the output as a package listing.
		return packages.PackageListing(pkgs)

	def groupinstall(self, group):
		pkgs = self.grouplist(group)

		self.install(pkgs)

	def grouplist(self, group):
		pkgs = self.repos.get_by_group(group)

		pkgs = packages.PackageListing(pkgs)
		pkgs.unique()

		return [p.name for p in pkgs]

	@staticmethod
	def build(pkg, resultdirs=None, **kwargs):
		if not resultdirs:
			resultdirs = []

		b = builder.Builder(pkg, **kwargs)
		p = b.pakfire

		# Always include local repository.
		resultdirs.append(p.repos.local_build.path)

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

	@staticmethod
	def shell(pkg, **kwargs):
		b = builder.Builder(pkg, **kwargs)

		try:
			b.prepare()
			b.extract()
			b.shell()
		finally:
			b.destroy()

	@staticmethod
	def dist(pkg, resultdirs=None, **pakfire_args):
		b = builder.Builder(pkg, **pakfire_args)
		p = b.pakfire

		if not resultdirs:
			resultdirs = []

		# Always include local repository
		resultdirs.append(p.repos.local_build.path)

		try:
			b.prepare()
			b.extract(build_deps=False)

			# Run the actual dist.
			b.dist()

			# Copy-out all resultfiles
			for resultdir in resultdirs:
				if not resultdir:
					continue

				b.copy_result(resultdir)
		finally:
			b.destroy()

	def provides(self, patterns):
		pkgs = []
		for pattern in patterns:
			requires = depsolve.Requires(None, pattern)
			pkgs += self.repos.get_by_provides(requires)

		pkgs = packages.PackageListing(pkgs)
		#pkgs.unique()

		return pkgs

	def requires(self, patterns):
		pkgs = []
		for pattern in patterns:
			requires = depsolve.Requires(None, pattern)
			pkgs += self.repos.get_by_requires(requires)

		pkgs = packages.PackageListing(pkgs)
		#pkgs.unique()

		return pkgs

	def repo_create(self, path, input_paths):
		repo = repository.LocalBinaryRepository(
			self,
			name="new",
			description="New repository.",
			path=path,
		)

		for input_path in input_paths:
			repo._collect_packages(input_path)

		repo.save()

	def repo_list(self):
		return self.repos.all
