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
import satsolver
import util

from constants import *
from i18n import _

class Pakfire(object):
	RELATIONS = (
		(">=", satsolver.REL_GE,),
		("<=", satsolver.REL_LE,),
		("=" , satsolver.REL_EQ,),
		("<" , satsolver.REL_LT,),
		(">" , satsolver.REL_GT,),
	)

	def __init__(self, mode=None, path="/", configs=[],
			enable_repos=None, disable_repos=None,
			distro_config=None):

		# Set the mode.
		assert mode in ("normal", "builder", "repo", "server", "master")
		self.mode = mode

		# Check if we are operating as the root user.
		self.check_root_user()

		# The path where we are operating in.
		self.path = path

		# Configure the instance of Pakfire we just started.
		if mode == "builder":
			self.path = os.path.join(BUILD_ROOT, util.random_string())

		elif mode == "normal":
			# check if we are actually running on an ipfire system.
			if self.path == "/":
				self.check_is_ipfire()

		# Read configuration file(s)
		self.config = config.Config(type=mode)
		for filename in configs:
			self.config.read(filename)

		# Setup the logger
		logger.setup_logging(self.config)
		self.config.dump()

		# Get more information about the distribution we are running
		# or building
		self.distro = distro.Distribution(self, distro_config)
		self.pool   = satsolver.Pool(self.distro.arch)
		self.repos  = repository.Repositories(self,
			enable_repos=enable_repos, disable_repos=disable_repos)

	def __del__(self):
		# Reset logging.
		logger.setup_logging()

	def create_solver(self):
		return satsolver.Solver(self, self.pool)

	def create_request(self):
		return satsolver.Request(self.pool)

	def create_relation(self, s):
		assert s

		if s.startswith("/"):
			return satsolver.Relation(self.pool, s)

		for pattern, type in self.RELATIONS:
			if not pattern in s:
				continue

			name, version = s.split(pattern, 1)

			return satsolver.Relation(self.pool, name, version, type)

		return satsolver.Relation(self.pool, s)

	def destroy(self):
		if not self.path == "/":
			util.rm(self.path)

	@property
	def supported_arches(self):
		return self.config.supported_arches

	def check_root_user(self):
		if not os.getuid() == 0 or not os.getgid() == 0:
			raise Exception, "You must run pakfire as the root user."

	def check_build_mode(self):
		"""
			Check if we are running in build mode.
			Otherwise, raise an exception.
		"""
		if not self.mode == "builder":
			raise BuildError, "Cannot build when not in build mode."

	def check_host_arch(self, arch):
		"""
			Check if we can build for arch.
		"""
		# If no arch was given on the command line we build for our
		# own arch which should always work.
		if not arch:
			return True

		if not self.config.host_supports_arch(arch):
			raise BuildError, "Cannot build for the target architecture: %s" % arch

		raise BuildError, arch

	def check_is_ipfire(self):
		ret = os.path.exists("/etc/ipfire-release")

		if not ret:
			raise NotAnIPFireSystemError, "You can run pakfire only on an IPFire system"

	@property
	def builder(self):
		# XXX just backwards compatibility
		return self.mode == "builder"

	def install(self, requires):
		# Create a new request.
		request = self.create_request()
		for req in requires:
			request.install(req)

		# Do the solving.
		solver = self.create_solver()
		t = solver.solve(request)

		if not t:
			return

		# Ask if the user acknowledges the transaction.
		if not t.cli_yesno():
			return

		# Run the transaction.
		t.run()

	def localinstall(self, files):
		repo_name = repo_desc = "localinstall"

		# Create a new repository that holds all packages we passed on
		# the commandline.
		repo = repository.RepositoryDir(self, repo_name, repo_desc,
			os.path.join(LOCAL_TMP_PATH, "repo_%s" % util.random_string()))

		# Register the repository.
		self.repos.add_repo(repo)

		try:
			# Add all packages to the repository index.
			for file in files:
				repo.collect_packages(file)

			# Break if no packages were added at all.
			if not len(repo):
				logging.critical(_("There are no packages to install."))
				return

			# Create a new request that installs all solvables from the
			# repository.
			request = self.create_request()
			for solv in [p.solvable for p in repo]:
				request.install(solv)

			solver = self.create_solver()
			t = solver.solve(request)

			# If solving was not possible, we exit here.
			if not t:
				return

			# Ask the user if this is okay.
			if not t.cli_yesno():
				return

			# If okay, run the transcation.
			t.run()

		finally:
			# Remove the temporary copy of the repository we have created earlier.
			repo.remove()

	def update(self, pkgs):
		request = self.create_request()

		# If there are given any packets on the command line, we will
		# only update them. Otherwise, we update the whole system.
		if pkgs:
			update = False
			for pkg in pkgs:
				request.update(pkg)
		else:
			update = True

		solver = self.create_solver()
		t = solver.solve(request, update=update)

		if not t:
			return

		# Ask the user if the transaction is okay.
		if not t.cli_yesno():
			return

		# Run the transaction.
		t.run()

	def remove(self, pkgs):
		# Create a new request.
		request = self.create_request()
		for pkg in pkgs:
			request.remove(pkg)

		# Solve the request.
		solver = self.create_solver()
		t = solver.solve(request, uninstall=True)

		if not t:
			return

		# Ask the user if okay.
		if not t.cli_yesno():
			return

		# Process the transaction.
		t.run()

	def info(self, patterns):
		pkgs = []

		# For all patterns we run a single search which returns us a bunch
		# of solvables which are transformed into Package objects.
		for pattern in patterns:
			solvs = self.pool.search(pattern, satsolver.SEARCH_GLOB, "solvable:name")

			for solv in solvs:
				pkgs.append(packages.SolvPackage(self, solv))

		return packages.PackageListing(pkgs)

	def search(self, pattern):
		# Do the search.
		pkgs = []
		for solv in self.pool.search(pattern, satsolver.SEARCH_STRING|satsolver.SEARCH_FILES):
			pkgs.append(packages.SolvPackage(self, solv))

		# Return the output as a package listing.
		return packages.PackageListing(pkgs)

	def groupinstall(self, group):
		pkgs = self.grouplist(group)

		self.install(pkgs)

	def grouplist(self, group):
		pkgs = []

		for solv in self.pool.search(group, satsolver.SEARCH_SUBSTRING, "solvable:group"):
			pkg = packages.SolvPackage(self, solv)

			if group in pkg.groups and not pkg.name in pkgs:
				pkgs.append(pkg.name)

		return sorted(pkgs)

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
			pkgs += self.repos.whatprovides(pattern)

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

	def repo_create(self, path, input_paths, type="binary"):
		assert type in ("binary", "source",)

		repo = repository.RepositoryDir(
			self,
			name="new",
			description="New repository.",
			path=path,
			type=type,
		)

		for input_path in input_paths:
			repo.collect_packages(input_path)

		repo.save()

		return repo

	def repo_list(self):
		return [r for r in self.repos]

	def clean_all(self):
		logging.debug("Cleaning up everything...")

		# Clean up repository caches.
		self.repos.clean()
