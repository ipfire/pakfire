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

import logging
import os
import random
import string

import actions
import builder
import config
import distro
import filelist
import logger
import packages
import repository
import satsolver
import transaction
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
			distro_config=None, **kwargs):

		# Set the mode.
		assert mode in ("normal", "builder", "server",)
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
		# Assume, that all other keyword arguments are configuration
		# parameters.
		self.config.update(kwargs)

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

	def create_request(self, builder=False):
		request = satsolver.Request(self.pool)

		# Add multiinstall information.
		for solv in PAKFIRE_MULTIINSTALL:
			request.noobsoletes(solv)

		return request

	def create_relation(self, s):
		assert s

		if isinstance(s, filelist._File):
			return satsolver.Relation(self.pool, s.name)

		elif s.startswith("/"):
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
	def environ(self):
		env = {}

		# Get distribution information.
		env.update(self.distro.environ)

		return env

	@property
	def supported_arches(self):
		return self.config.supported_arches

	@property
	def offline(self):
		"""
			A shortcut that indicates if the system is running in offline mode.
		"""
		return self.config.get("offline", False)

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
		return # XXX disabled for now

		ret = os.path.exists("/etc/ipfire-release")

		if not ret:
			raise NotAnIPFireSystemError, "You can run pakfire only on an IPFire system"

	@property
	def builder(self):
		# XXX just backwards compatibility
		return self.mode == "builder"

	def resolvdep(self, requires):
		# Create a new request.
		request = self.create_request()
		for req in requires:
			req = self.create_relation(req)
			request.install(req)

		# Do the solving.
		solver = self.create_solver()
		t = solver.solve(request)

		if t:
			t.dump()
		else:
			logging.info(_("Nothing to do"))

	def install(self, requires, interactive=True, logger=None, **kwargs):
		if not logger:
			logger = logging.getLogger()

		# Create a new request.
		request = self.create_request()

		# Expand all groups.
		for req in requires:
			if req.startswith("@"):
				reqs = self.grouplist(req[1:])
			else:
				reqs = [req,]

			for req in reqs:
				if not isinstance(req, packages.BinaryPackage):
					req = self.create_relation(req)

				request.install(req)

		# Do the solving.
		solver = self.create_solver()
		t = solver.solve(request, **kwargs)

		if not t:
			if not interactive:
				raise DependencyError

			logging.info(_("Nothing to do"))
			return

		if interactive:
			# Ask if the user acknowledges the transaction.
			if not t.cli_yesno():
				return

		else:
			t.dump(logger=logger)

		# Run the transaction.
		t.run()

	def localinstall(self, files, yes=None, allow_uninstall=False):
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
			t = solver.solve(request, uninstall=allow_uninstall)

			# If solving was not possible, we exit here.
			if not t:
				logging.info(_("Nothing to do"))
				return

			if yes is None:
				# Ask the user if this is okay.
				if not t.cli_yesno():
					return
			elif yes:
				t.dump()
			else:
				return

			# If okay, run the transcation.
			t.run()

		finally:
			# Remove the temporary copy of the repository we have created earlier.
			repo.remove()
			self.repos.rem_repo(repo)

	def reinstall(self, pkgs, strict=False):
		"""
			Reinstall one or more packages.

			If strict is True, only a package with excatly the same UUID
			will replace the currently installed one.
		"""
		# XXX it is possible to install packages without fulfulling
		# all dependencies.

		reinstall_pkgs = []
		for pattern in pkgs:
			_pkgs = []
			for pkg in self.repos.whatprovides(pattern):
				# Do not reinstall non-installed packages.
				if not pkg.is_installed():
					continue

				_pkgs.append(pkg)

			if not _pkgs:
				logging.warning(_("Could not find any installed package providing \"%s\".") \
					% pattern)
			elif len(_pkgs) == 1:
				reinstall_pkgs.append(_pkgs[0])
				#t.add("reinstall", _pkgs[0])
			else:
				logging.warning(_("Multiple reinstall candidates for \"%s\": %s") \
					% (pattern, ", ".join(p.friendly_name for p in sorted(_pkgs))))

		if not reinstall_pkgs:
			logging.info(_("Nothing to do"))
			return

		# Packages we want to replace.
		# Contains a tuple with the old and the new package.
		pkgs = []

		# Find the package that is installed in a remote repository to
		# download it again and re-install it. We need that.
		for pkg in reinstall_pkgs:
			# Collect all candidates in here.
			_pkgs = []

			provides = "%s=%s" % (pkg.name, pkg.friendly_version)
			for _pkg in self.repos.whatprovides(provides):
				if _pkg.is_installed():
					continue

				if strict:
					if pkg.uuid == _pkg.uuid:
						_pkgs.append(_pkg)
				else:
					_pkgs.append(_pkg)

			if not _pkgs:
				logging.warning(_("Could not find package %s in a remote repository.") % \
					pkg.friendly_name)
			else:
				# Sort packages to reflect repository priorities, etc...
				# and take the best (first) one.
				_pkgs.sort()

				# Re-install best package and cleanup the old one.
				pkgs.append((pkg, _pkgs[0]))

		# Eventually, create a request.
		request = None

		_pkgs = []
		for old, new in pkgs:
			if old.uuid == new.uuid:
				_pkgs.append((old, new))
			else:
				if request is None:
					# Create a new request.
					request = self.create_request()

				# Install the new package, the old will
				# be cleaned up automatically.
				request.install(new.solvable)

		if request:
			solver = self.create_solver()
			t = solver.solve(request)
		else:
			# Create new transaction.
			t = transaction.Transaction(self)

		for old, new in _pkgs:
			# Install the new package and remove the old one.
			t.add(actions.ActionReinstall.type, new)
			t.add(actions.ActionCleanup.type, old)

		t.sort()

		if not t:
			logging.info(_("Nothing to do"))
			return

		if not t.cli_yesno():
			return

		t.run()

	def update(self, pkgs, check=False, excludes=None, allow_vendorchange=False, allow_archchange=False):
		"""
			check indicates, if the method should return after calculation
			of the transaction.
		"""
		request = self.create_request()

		# If there are given any packets on the command line, we will
		# only update them. Otherwise, we update the whole system.
		if pkgs:
			update = False
			for pkg in pkgs:
				pkg = self.create_relation(pkg)
				request.update(pkg)
		else:
			update = True

		# Exclude packages that should not be updated.
		if excludes:
			for exclude in excludes:
				logging.info(_("Excluding %s.") % exclude)

				exclude = self.create_relation(exclude)
				request.lock(exclude)

		solver = self.create_solver()
		t = solver.solve(request, update=update,
			allow_vendorchange=allow_vendorchange,
			allow_archchange=allow_archchange)

		if not t:
			logging.info(_("Nothing to do"))

			# If we are running in check mode, we return a non-zero value to
			# indicate, that there are no updates.
			if check:
				return 1
			else:
				return

		# Just exit here, because we won't do the transaction in this mode.
		if check:
			t.dump()
			return

		# Ask the user if the transaction is okay.
		if not t.cli_yesno():
			return

		# Run the transaction.
		t.run()

	def downgrade(self, pkgs, allow_vendorchange=False, allow_archchange=False):
		assert pkgs

		# Create a new request.
		request = self.create_request()

		# Fill request.
		for pattern in pkgs:
			best = None
			for pkg in self.repos.whatprovides(pattern):
				# Only consider installed packages.
				if not pkg.is_installed():
					continue

				if best and pkg > best:
					best = pkg
				elif best is None:
					best = pkg

			if best is None:
				logging.warning(_("\"%s\" package does not seem to be installed.") % pattern)
			else:
				rel = self.create_relation("%s<%s" % (best.name, best.friendly_version))
				request.install(rel)

		# Solve the request.
		solver = self.create_solver()
		t = solver.solve(request, allow_downgrade=True,
			allow_vendorchange=allow_vendorchange,
			allow_archchange=allow_archchange)

		if not t:
			logging.info(_("Nothing to do"))
			return

		if not t.cli_yesno():
			return

		t.run()

	def remove(self, pkgs):
		# Create a new request.
		request = self.create_request()
		for pkg in pkgs:
			pkg = self.create_relation(pkg)
			request.remove(pkg)

		# Solve the request.
		solver = self.create_solver()
		t = solver.solve(request, uninstall=True)

		if not t:
			logging.info(_("Nothing to do"))
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
			if os.path.exists(pattern) and not os.path.isdir(pattern):
				pkg = packages.open(self, self.repos.dummy, pattern)
				if pkg:
					pkgs.append(pkg)

			else:
				solvs = self.pool.search(pattern, satsolver.SEARCH_GLOB, "solvable:name")

				for solv in solvs:
					pkg = packages.SolvPackage(self, solv)
					if pkg in pkgs:
						continue

					pkgs.append(pkg)

		return sorted(pkgs)

	def search(self, pattern):
		# Do the search.
		pkgs = {}
		for solv in self.pool.search(pattern, satsolver.SEARCH_STRING|satsolver.SEARCH_FILES):
			pkg = packages.SolvPackage(self, solv)

			# Check, if a package with the name is already in the resultset
			# and always replace older ones by more recent ones.
			if pkgs.has_key(pkg.name):
				if pkgs[pkg.name] < pkg:
					pkgs[pkg.name] = pkg
			else:
				pkgs[pkg.name] = pkg

		# Return a list of the packages, alphabetically sorted.
		return sorted(pkgs.values())

	def groupinstall(self, group, **kwargs):
		self.install("@%s" % group, **kwargs)

	def grouplist(self, group):
		pkgs = []

		for solv in self.pool.search(group, satsolver.SEARCH_SUBSTRING, "solvable:group"):
			pkg = packages.SolvPackage(self, solv)

			if group in pkg.groups and not pkg.name in pkgs:
				pkgs.append(pkg.name)

		return sorted(pkgs)

	@staticmethod
	def build(pkg, resultdirs=None, shell=False, install_test=True, after_shell=False, **kwargs):
		if not resultdirs:
			resultdirs = []

		b = builder.BuildEnviron(pkg, **kwargs)
		p = b.pakfire

		# Always include local repository.
		resultdirs.append(p.repos.local_build.path)

		try:
			# Start to prepare the build environment by mounting
			# the filesystems and extracting files.
			b.start()

			try:
				# Build the package.
				b.build(install_test=install_test)
			except BuildError:
				# Raise the error, if the user does not want to
				# have a shell.
				if not shell:
					raise

				# Run a shell to debug the issue.
				b.shell()

			# If the user requests a shell after a successful build,
			# we run it here.
			if after_shell:
				b.shell()

			# Copy-out all resultfiles if the build was successful.
			for resultdir in resultdirs:
				if not resultdir:
					continue

				b.copy_result(resultdir)
		finally:
			b.stop()

	def _build(self, pkg, resultdir, nodeps=False, **kwargs):
		b = builder.Builder(self, pkg, resultdir, **kwargs)

		try:
			b.build()
		except Error:
			raise BuildError, _("Build command has failed.")

		# If the build was successful, cleanup all temporary files.
		b.cleanup()

	@staticmethod
	def shell(pkg, **kwargs):
		b = builder.BuildEnviron(pkg, **kwargs)

		try:
			b.start()
			b.shell()
		finally:
			b.stop()

	def dist(self, pkgs, resultdirs=None):
		assert resultdirs

		for pkg in pkgs:
			pkg = packages.Makefile(self, pkg)

			pkg.dist(resultdirs)

	def provides(self, patterns):
		pkgs = []
		for pattern in patterns:
			for pkg in self.repos.whatprovides(pattern):
				if pkg in pkgs:
					continue

				pkgs.append(pkg)

		return sorted(pkgs)

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

	def check(self, downgrade=True, uninstall=True):
		"""
			Try to fix any errors in the system.
		"""
		# Detect any errors in the dependency tree.
		# For that we create an empty request and solver and try to solve
		# something.
		request = self.create_request()
		solver = self.create_solver()

		# XXX the solver does crash if we call it with fix_system=1,
		# allow_downgrade=1 and uninstall=1. Need to fix this.
		allow_downgrade = False
		uninstall = False

		t = solver.solve(request, fix_system=True, allow_downgrade=downgrade,
			uninstall=uninstall)

		if not t:
			logging.info(_("Everything is fine."))
			return

		# Ask the user if okay.
		if not t.cli_yesno():
			return

		# Process the transaction.
		t.run()
