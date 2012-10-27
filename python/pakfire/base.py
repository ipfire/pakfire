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
import random
import string

import actions
import builder
import distro
import filelist
import keyring
import logger
import packages
import repository
import satsolver
import transaction
import util

import logging
log = logging.getLogger("pakfire")

from config import Config
from constants import *
from i18n import _

class Pakfire(object):
	mode = None

	RELATIONS = (
		(">=", satsolver.REL_GE,),
		("<=", satsolver.REL_LE,),
		("=" , satsolver.REL_EQ,),
		("<" , satsolver.REL_LT,),
		(">" , satsolver.REL_GT,),
	)

	def __init__(self, path="/", config=None, configs=None, arch=None,
			enable_repos=None, disable_repos=None, **kwargs):
		# Check if we are operating as the root user.
		self.check_root_user()

		# The path where we are operating in.
		self.path = path

		# Configure the instance of Pakfire we just started.
		if self.mode == "builder":
			self.path = os.path.join(BUILD_ROOT, util.random_string())

		elif not mode:
			# check if we are actually running on an ipfire system.
			if self.path == "/":
				self.check_is_ipfire()

		# Get the configuration.
		if config:
			assert configs is None, "You cannot pass configs and config."
			self.config = config
		else:
			# Read configuration file(s).
			self.config = Config(files=configs)

		# Update configuration with additional arguments.
		for section, settings in kwargs.items():
			self.config.update(section, settings)

		# Dump the configuration.
		self.config.dump()

		# Initialize the keyring.
		self.keyring = keyring.Keyring(self)

		# Get more information about the distribution we are running
		# or building
		self.distro = distro.Distribution(self)
		if arch:
			self.distro.arch = arch

		self.pool   = satsolver.Pool(self.distro.arch)
		self.repos  = repository.Repositories(self,
			enable_repos=enable_repos, disable_repos=disable_repos)

	def __del__(self):
		# Reset logging.
		logger.setup_logging()

	def expand_requires(self, requires):
		if requires is None:
			return []

		ret = []
		for req in requires:
			if isinstance(req, packages.BinaryPackage):
				ret.append(req)
				continue

			if isinstance(req, packages.SolvPackage):
				ret.append(req.solvable)
				continue

			assert type(req) == type("a"), req

			# Expand all groups.
			if req.startswith("@"):
				reqs = self.grouplist(req[1:])
			else:
				reqs = [req,]

			for req in reqs:
				req = self.create_relation(req)
				ret.append(req)

		return ret

	def create_request(self, builder=False, install=None, remove=None, update=None, updateall=False):
		request = satsolver.Request(self.pool)

		# Add multiinstall information.
		for solv in PAKFIRE_MULTIINSTALL:
			request.noobsoletes(solv)

		# Apply all installs.
		for req in self.expand_requires(install):
			request.install(req)

		# Apply all removes.
		for req in self.expand_requires(remove):
			request.remove(req)

		# Apply all updates.
		for req in self.expand_requires(update):
			request.update(req)

		# Configure the request to update all packages
		# if requested.
		if updateall:
			request.updateall()

		# Return the request.
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

			# Trim spaces from strings.
			name = name.strip()
			version = version.strip()

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
		return system.supported_arches

	@property
	def offline(self):
		"""
			A shortcut that indicates if the system is running in offline mode.
		"""
		return self.config.get("downloader", "offline", False)

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

		if not system.host_supports_arch(arch):
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

	def resolvdep(self, pkg, logger=None):
		assert os.path.exists(pkg)

		# Open the package file.
		pkg = packages.open(self, None, pkg)

		# Create a new request.
		request = self.create_request(install=pkg.requires)

		# Add build dependencies if needed.
		if isinstance(pkg, packages.Makefile) or isinstance(pkg, packages.SourcePackage):
			for req in self.expand_requires(BUILD_PACKAGES):
				request.install(req)

		# Solv the request.
		solver = self.solv(request, logger=logger)

		if solver.status:
			return solver

		raise DependencyError, solver.get_problem_string()

	def solv(self, request, interactive=False, logger=None, **kwargs):
		# XXX implement interactive

		if not logger:
			logger = logging.getLogger("pakfire")

		# Create a solver.
		solver = satsolver.Solver(self, request, logger=logger)

		# Apply configuration to solver.
		for key, val in kwargs.items():
			solver.set(key, val)

		# Do the solving.
		solver.solve()

		# Return the solver so one can do stuff with it...
		return solver

	def install(self, requires, interactive=True, logger=None, signatures_mode=None, **kwargs):
		if not logger:
			logger = logging.getLogger("pakfire")

		# Pointer to temporary repository.
		repo = None

		# Sort out what we got...
		files = []
		relations = []

		for req in requires:
			if isinstance(req, packages.Package):
				relations.append(req)
				continue

			# This looks like a file.
			if req.endswith(".%s" % PACKAGE_EXTENSION) and os.path.exists(req):
				files.append(req)
				continue

			# We treat the rest as relations. The solver will return any errors.
			relations.append(req)

		# Redefine requires, which will be the list that will be passed to the
		# solver.
		requires = relations

		try:
			# If we have got files to install, we need to create a temporary repository
			# called 'localinstall'.
			# XXX FIX TMP PATH
			if files:
				repo = repository.RepositoryDir(self, "localinstall", _("Local install repository"),
					os.path.join(LOCAL_TMP_PATH, "repo_%s" % util.random_string()))

				# Register the repository.
				self.repos.add_repo(repo)

				# Add all packages to the repository index.
				repo.add_packages(*files)

				# Add all packages to the requires.
				requires += repo

			# Do the solving.
			request = self.create_request(install=requires)
			solver  = self.solv(request, logger=logger, interactive=interactive, **kwargs)

			# Create the transaction.
			t = solver.transaction
			t.dump(logger=logger)

			# Ask if the user acknowledges the transaction.
			if interactive and not t.cli_yesno():
				return

			# Run the transaction.
			t.run(logger=logger, signatures_mode=signatures_mode)

		finally:
			if repo:
				# Remove the temporary repository we have created earlier.
				repo.remove()
				self.repos.rem_repo(repo)

	def reinstall(self, pkgs, strict=False, logger=None):
		"""
			Reinstall one or more packages.

			If strict is True, only a package with excatly the same UUID
			will replace the currently installed one.
		"""
		if logger is None:
			logger = logging.getLogger("pakfire")

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
				logger.warning(_("Could not find any installed package providing \"%s\".") \
					% pattern)
			elif len(_pkgs) == 1:
				reinstall_pkgs.append(_pkgs[0])
				#t.add("reinstall", _pkgs[0])
			else:
				logger.warning(_("Multiple reinstall candidates for \"%(pattern)s\": %(pkgs)s") \
					% { "pattern" : pattern, "pkgs" : ", ".join(p.friendly_name for p in sorted(_pkgs)) })

		if not reinstall_pkgs:
			logger.info(_("Nothing to do"))
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
				logger.warning(_("Could not find package %s in a remote repository.") % \
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
			solver = self.solv(request)
			assert solver.status

			t = solver.transaction
		else:
			# Create new transaction.
			t = transaction.Transaction(self)

		for old, new in _pkgs:
			# Install the new package and remove the old one.
			t.add(actions.ActionReinstall.type, new)
			t.add(actions.ActionCleanup.type, old)

		t.sort()

		if not t:
			logger.info(_("Nothing to do"))
			return

		t.dump(logger=logger)

		if not t.cli_yesno():
			return

		t.run(logger=logger)

	def update(self, pkgs=None, check=False, excludes=None, interactive=True, logger=None, **kwargs):
		"""
			check indicates, if the method should return after calculation
			of the transaction.
		"""
		if logger is None:
			logger = logging.getLogger("pakfire")

		# If there are given any packets on the command line, we will
		# only update them. Otherwise, we update the whole system.
		updateall = True
		if pkgs:
			updateall = False

		request = self.create_request(update=pkgs, updateall=updateall)

		# Exclude packages that should not be updated.
		for exclude in excludes or []:
			logger.info(_("Excluding %s.") % exclude)

			exclude = self.create_relation(exclude)
			request.lock(exclude)

		solver = self.solv(request, logger=logger, **kwargs)

		if not solver.status:
			logger.info(_("Nothing to do"))

			# If we are running in check mode, we return a non-zero value to
			# indicate, that there are no updates.
			if check:
				return 1
			else:
				return

		# Create the transaction.
		t = solver.transaction
		t.dump(logger=logger)

		# Just exit here, because we won't do the transaction in this mode.
		if check:
			return

		# Ask the user if the transaction is okay.
		if interactive and not t.cli_yesno():
			return

		# Run the transaction.
		t.run(logger=logger)

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
				log.warning(_("\"%s\" package does not seem to be installed.") % pattern)
			else:
				rel = self.create_relation("%s<%s" % (best.name, best.friendly_version))
				request.install(rel)

		# Solve the request.
		solver = self.solv(request,
			allow_downgrade=True,
			allow_vendorchange=allow_vendorchange,
			allow_archchange=allow_archchange,
		)
		assert solver.status is True

		# Create the transaction.
		t = solver.transaction
		t.dump(logger=logger)

		if not t:
			log.info(_("Nothing to do"))
			return

		if not t.cli_yesno():
			return

		t.run()

	def remove(self, pkgs):
		# Create a new request.
		request = self.create_request(remove=pkgs)

		# Solve the request.
		solver = self.solv(request, allow_uninstall=True)
		assert solver.status is True

		# Create the transaction.
		t = solver.transaction
		t.dump()

		if not t:
			log.info(_("Nothing to do"))
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

	def _build(self, pkg, resultdir, nodeps=False, prepare=False, **kwargs):
		b = builder.Builder(self, pkg, resultdir, **kwargs)

		stages = None
		if prepare:
			stages = ("prepare",)

		try:
			b.build(stages=stages)

		except Error:
			raise BuildError, _("Build command has failed.")

		# If the build was successful, cleanup all temporary files.
		b.cleanup()

	@staticmethod
	def shell(pkg, **kwargs):
		b = builder.BuildEnviron(pkg, **kwargs)

		try:
			b.start()

			try:
				b.build(prepare=True)
			except BuildError:
				pass

			b.shell()
		finally:
			b.stop()

	def dist(self, pkg, resultdir):
		pkg = packages.Makefile(self, pkg)

		return pkg.dist(resultdir=resultdir)

	def provides(self, patterns):
		pkgs = []
		for pattern in patterns:
			for pkg in self.repos.whatprovides(pattern):
				if pkg in pkgs:
					continue

				pkgs.append(pkg)

		return sorted(pkgs)

	def repo_create(self, path, input_paths, name=None, key_id=None, type="binary"):
		assert type in ("binary", "source",)

		if not name:
			name = _("New repository")

		# Create new repository.
		repo = repository.RepositoryDir(self, name=name, description="New repository.",
			path=path, type=type, key_id=key_id)

		# Add all packages.
		repo.add_packages(*input_paths)

		# Write metadata to disk.
		repo.save()

		# Return the new repository.
		return repo

	def repo_list(self):
		return [r for r in self.repos]

	def clean_all(self):
		log.debug("Cleaning up everything...")

		# Clean up repository caches.
		self.repos.clean()

	def check(self, allow_downgrade=True, allow_uninstall=True):
		"""
			Try to fix any errors in the system.
		"""
		# Detect any errors in the dependency tree.
		# For that we create an empty request and solver and try to solve
		# something.
		request = self.create_request()
		request.verify()

		solver = self.solv(
			request,
			allow_downgrade=allow_downgrade,
			allow_uninstall=allow_uninstall,
		)

		if solver.status is False:
			log.info(_("Everything is fine."))
			return

		# Create the transaction.
		t = solver.transaction
		t.dump()

		# Ask the user if okay.
		if not t.cli_yesno():
			return

		# Process the transaction.
		t.run()


class PakfireBuilder(Pakfire):
	mode = "builder"


class PakfireServer(Pakfire):
	mode = "server"
