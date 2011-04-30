#!/usr/bin/python

import logging
import os
import random
import string

import builder
import config
import distro
import logger
import repository
import packages
import util

from constants import *
from i18n import _

class Pakfire(object):
	def __init__(self, builder=False, configs=[], enable_repos=None,
			disable_repos=None, distro_config=None):
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
		self.repos  = repository.Repositories(self,
			enable_repos=enable_repos, disable_repos=disable_repos)

		# Create a short reference to the solver of this pakfire instance.
		self.solver = self.repos.solver

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
		# Create a new request.
		request = self.solver.create_request()
		for req in requires:
			request.install(req)

		# Do the solving.
		t = self.solver.solve(request)

		if not t:
			return

		t.run()

	def localinstall(self, files):
		repo_name = "localinstall"

		# Create a new repository that holds all packages we passed on
		# the commandline.
		repo = self.solver.pool.create_repo(repo_name)

		# Open all passed files and try to open them.
		for file in files:
			pkg = packages.open(self, None, file)

			if not isinstance(pkg, packages.BinaryPackage):
				logging.warning("Skipping package which is a wrong format: %s" % file)
				continue

			# Add the package information to the solver.
			self.solver.add_package(pkg, repo_name)

		# Break if no packages were added at all.
		if not repo.size():
			logging.critical("There are no packages to install.")
			return

		# Create a new request which contains all solvabled from the CLI and
		# try to solve it.
		request = self.solver.create_request()
		for solvable in repo:
			print solvable
			request.install(solvable)

		t = self.solver.solve(request)

		# If solving was not possible, we exit here.
		if not t:
			return

		# Otherwise we run the transcation.
		t.run()

	def update(self, pkgs):
		# XXX needs to be done
		pass

	def info(self, patterns):
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
	def build(pkg, resultdirs=None, shell=False, **kwargs):
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
			if shell:
				b.shell()
			else:
				raise

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
	def dist(pkgs, resultdirs=None, **pakfire_args):
		# Create a builder with empty package.
		b = builder.Builder(None, **pakfire_args)
		p = b.pakfire

		if not resultdirs:
			resultdirs = []

		# Always include local repository
		resultdirs.append(p.repos.local_build.path)

		try:
			b.prepare()

			for pkg in pkgs:
				b.pkg = pkg

				b.extract(build_deps=False)

				# Run the actual dist.
				b.dist()

				# Copy-out all resultfiles
				for resultdir in resultdirs:
					if not resultdir:
						continue

					b.copy_result(resultdir)

				# Cleanup the stuff that the package left.
				b.cleanup()
		finally:
			b.destroy()

	def provides(self, patterns):
		pkgs = []
		for pattern in patterns:
			pkgs += self.repos.get_by_provides(pattern)

		pkgs = packages.PackageListing(pkgs)
		#pkgs.unique()

		return pkgs

	def requires(self, patterns):
		pkgs = []
		for pattern in patterns:
			pkgs += self.repos.get_by_requires(pattern)

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
