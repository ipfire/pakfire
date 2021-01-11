#!/usr/bin/python3
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

from . import _pakfire
from . import distro
from . import downloaders
from . import logger
from . import packages
from . import repository
from . import util

from .config import Config
from .system import system

from .constants import *
from .i18n import _

class Pakfire(_pakfire.Pakfire):
	__version__ = PAKFIRE_VERSION

	def __init__(self, path="/", config=None, arch=None, distro=None, cache_path=None, offline=False):
		_pakfire.Pakfire.__init__(self, path, arch)

		# Initialise logging system
		self.log = self._setup_logger()

		# Default to system distribution
		self.distro = distro or system.distro

		# Offline
		self.offline = offline

		# Check if we are operating as the root user
		self.check_root_user()

		# check if we are actually running on an ipfire system
		if self.path == "/":
			self.check_is_ipfire()

		# Load configuration
		self.config = config or Config("general.conf")

		self.cache_path = cache_path or \
			os.path.join(CACHE_DIR, self.distro.sname, self.distro.release)

		self.repos = repository.Repositories(self)

		# Load default repository configuration
		repos_dir = self.make_path(CONFIG_REPOS_DIR)
		if repos_dir:
			self.repos.load_configuration(repos_dir)

	def _setup_logger(self):
		log = logging.getLogger("pakfire")
		log.propagate = 0

		# Always process all messages (include debug)
		log.setLevel(logging.DEBUG)

		# Pass everything down to libpakfire
		handler = logger.PakfireLogHandler(self)
		log.addHandler(handler)

		return log

	def make_path(self, path):
		"""
			Returns path relative to the (base)path
			of this Pakfire instance.
		"""
		while path.startswith("/"):
			path = path[1:]

		return os.path.join(self.path, path)

	def __enter__(self):
		"""
			Called to initialize this Pakfire instance when
			the context is entered.
		"""
		# Dump the configuration when we enter the context
		self.config.dump()

		# Refresh repositories
		self.refresh_repositories()

		return PakfireContext(self)

	def __exit__(self, type, value, traceback):
		pass

	def get_offline(self):
		"""
			A shortcut that indicates if the system is running in offline mode.
		"""
		return self._offline or self.config.get("downloader", "offline", False)

	def set_offline(self, offline):
		self._offline = offline

	offline = property(get_offline, set_offline)

	def refresh_repositories(self, force=False):
		for repo in self.repos:
			if not repo.enabled:
				continue

			if repo == self.installed_repo:
				continue

			d = downloaders.RepositoryDownloader(self, repo)
			d.refresh(force=force)

	def check_root_user(self):
		if not os.getuid() == 0 or not os.getgid() == 0:
			raise Exception("You must run pakfire as the root user.")

	def check_is_ipfire(self):
		ret = os.path.exists("/etc/ipfire-release")

		if not ret:
			raise NotIPFireError("You can run pakfire only on an IPFire system")

	def clean(self):
		# Clean up repository caches
		for repo in self.repos:
			repo.clean()

	def dist(self, pkg, resultdir):
		pkg = packages.Makefile(self, pkg)

		return pkg.dist(resultdir=resultdir)


class PakfireContext(object):
	"""
		This context has functions that require
		pakfire to be initialized.

		That means that repository data has to be downloaded
		and imported to be searchable, etc.
	"""
	def __init__(self, pakfire):
		self.pakfire = pakfire

	@property
	def repos(self):
		"""
			Shortcut to access any configured
			repositories for this Pakfire instance
		"""
		return self.pakfire.repos

	def check(self, **kwargs):
		"""
			Try to fix any errors in the system.
		"""
		# Detect any errors in the dependency tree.
		# For that we create an empty request and solver and try to solve
		# something.
		request = _pakfire.Request(self.pakfire)
		request.verify()

		return request.solve(**kwargs)

	def info(self, args):
		pkgs = []

		with _pakfire.Repo(self.pakfire, "tmp", clean=True) as r:
			for arg in args:
				if os.path.exists(arg) and not os.path.isdir(arg):
					archive = _pakfire.Archive(self.pakfire, arg)

					# Add the archive to the repository
					pkg = r.add_archive(archive)
					pkgs.append(pkg)

				else:
					pkgs += self.pakfire.whatprovides(arg, name_only=True)

		return sorted(pkgs)

	def provides(self, patterns):
		pkgs = []

		for pattern in patterns:
			for pkg in self.pakfire.whatprovides(self, pattern):
				if pkg in pkgs:
					continue

				pkgs.append(pkg)

		return sorted(pkgs)

	def search(self, pattern):
		return self.pakfire.search(pattern)

	def extract(self, filenames, target=None):
		if target and target == "/":
			raise ValueError("Cannot extract to: %s" % target)

		archives = []

		# Open all archives
		for filename in filenames:
			a = _pakfire.Archive(self.pakfire, filename)
			archives.append(a)

		# Nothing to do when no archives where opened
		if not archives:
			return

		# Extract them all
		for archive in archives:
			archive.extract(target)

	# Transactions

	def install(self, requires, **kwargs):
		request = _pakfire.Request(self.pakfire)

		# XXX handle files and URLs

		for req in requires:
			# Handle groups
			# TODO should move into libpakfire
			if req.startswith("@"):
				sel = _pakfire.Selector(self.pakfire)
				sel.set(_pakfire.PAKFIRE_PKG_GROUP, _pakfire.PAKFIRE_EQ, req[1:])
				request.install(sel)
				continue

			# Handle everything else
			relation = _pakfire.Relation(self.pakfire, req)
			request.install(relation)

		return request.solve(**kwargs)

	def reinstall(self, pkgs, strict=False, logger=None):
		"""
			Reinstall one or more packages
		"""
		raise NotImplementedError

	def erase(self, pkgs, **kwargs):
		request = _pakfire.Request(self.pakfire)

		for pkg in pkgs:
			relation = _pakfire.Relation(self.pakfire, pkg)
			request.erase(relation)

		return request.solve(**kwargs)

	def update(self, reqs=None, excludes=None, **kwargs):
		request = _pakfire.Request(self.pakfire)

		# Add all packages that should be updated to the request
		for req in reqs or []:
			relation = _pakfire.Relation(self.pakfire, req)
			request.upgrade(relation)

		# Otherwise we will try to upgrade everything
		else:
			request.upgrade_all()

		# Exclude packages that should not be updated
		for exclude in excludes or []:
			relation = _pakfire.Relation(self.pakfire, exclude)
			request.lock(relation)

		return request.solve(**kwargs)

	def downgrade(self, pkgs, logger=None, **kwargs):
		assert pkgs

		if logger is None:
			logger = logging.getLogger("pakfire")

		# Create a new request.
		request = self.pakfire.create_request()

		# Fill request.
		for pattern in pkgs:
			best = None
			for pkg in self.pakfire.repos.whatprovides(pattern):
				# Only consider installed packages.
				if not pkg.is_installed():
					continue

				if best and pkg > best:
					best = pkg
				elif best is None:
					best = pkg

			if best is None:
				logger.warning(_("\"%s\" package does not seem to be installed.") % pattern)
			else:
				rel = self.pakfire.create_relation("%s < %s" % (best.name, best.friendly_version))
				request.install(rel)

		# Solve the request.
		solver = self.pakfire.solve(request, allow_downgrade=True, **kwargs)
		assert solver.status is True

		# Create the transaction.
		t = transaction.Transaction.from_solver(self.pakfire, solver)
		t.dump(logger=logger)

		if not t:
			logger.info(_("Nothing to do"))
			return

		if not t.cli_yesno():
			return

		t.run()


class PakfireServer(Pakfire):
	def repo_create(self, path, input_paths, name=None, key_id=None, type="binary"):
		assert type in ("binary", "source",)

		if not name:
			name = _("New repository")

		# Create new repository.
		repo = repository.RepositoryDir(self, name=name, description="New repository.",
			path=path, key_id=key_id)

		# Add all packages.
		repo.add_packages(input_paths)

		# Write metadata to disk.
		repo.save()

		# Return the new repository.
		return repo


class PakfireKey(Pakfire):
	pass
