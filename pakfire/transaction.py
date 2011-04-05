#!/usr/bin/python

import logging
import os
import progressbar
import sys
import tarfile

import depsolve
import packages
import util

from i18n import _

class ActionError(Exception):
	pass


class Action(object):
	def __init__(self, pakfire, pkg, deps=None):
		self.pakfire = pakfire
		self.pkg = pkg
		self.deps = deps or []

	def __cmp__(self, other):
		# XXX ugly
		return cmp(self.__repr__(), other.__repr__())

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.pkg.friendly_name)

	def remove_dep(self, dep):
		if not self.deps:
			return

		while dep in self.deps:
			logging.debug("Removing dep %s from %s" % (dep, self))
			self.deps.remove(dep)

	def run(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Reference to local repository (database).
		"""
		return self.pakfire.repos.local


class ActionCleanup(Action):
	def gen_files(self):
		"""
			Return a list of all files that are not in the package anymore
			and so to be removed.
		"""
		files = []

		# Compare the filelist of the old and the new package and save the
		# difference.

		for f in self.pkg.old_package.filelist:
			if f in self.pkg.filelist:
				continue

			# Save absolute path.
			f = os.path.join(self.pakfire.path, f)
			files.append(f)

		return files

	def remove_files(self, message, files):
		if not files:
			return

		pb = util.make_progress(message, len(files))
		i = 0

		for f in self.gen_files():
			# Update progress if any.
			i += 1
			if pb:
				pb.update(i)

			# Skip non-existant files (mabye the user removed it already?)
			if not os.path.exists(f):
				continue

			logging.debug("Going to remove file: %s" % f)

			try:
				os.unlink(f)
			except:
				logging.critical("Could not remove file: %s. Do it manually." % f)

			# XXX remove file from database

		if pb:
			pb.finish()

	def run(self):
		files = self.gen_files()

		if not files:
			return

		self.remove_files(_("Cleanup: %s") % self.pkg.name, files)


class ActionScript(Action):
	def run(self):
		pass # XXX TBD


class ActionScriptPreIn(ActionScript):
	pass


class ActionScriptPostIn(ActionScript):
	pass


class ActionScriptPreUn(ActionScript):
	pass


class ActionScriptPostUn(ActionScript):
	pass


class ActionInstall(Action):
	def extract(self, message, prefix=None):
		logging.debug("Extracting package %s" % self.pkg.friendly_name)

		if prefix is None:
			prefix = self.pakfire.path

		self.pkg.extract(message, prefix=prefix)

		# Create package in the database
		self.local.index.add_package(self.pkg)

	def run(self):
		self.extract(_("Installing: %s") % self.pkg.name)


class ActionUpdate(ActionInstall):
	def run(self):
		self.extract(_("Updating: %s") % self.pkg.name)


class ActionRemove(ActionCleanup):
	def run(self):
		files = self.pkg.filelist

		if not files:
			return

		self.remove_files(_("Removing: %s") % self.pkg.name, files)


class TransactionSet(object):
	def __init__(self):
		self.installs = []
		self.install_deps = []

		self.updates = []
		self.update_deps = []

		self.removes = []
		self.remove_deps = []

	@property
	def download_lists(self):
		# All elements in these lists must be local.
		return (self.installs, self.install_deps, self.updates, self.update_deps)

	@property
	def downloads(self):
		"""
			Return a list containing all packages that need to be downloaded.
		"""
		pkgs = []
		for dl_list in self.download_lists:
			pkgs += dl_list

		pkgs.sort()

		for pkg in pkgs:
			# Skip all packages that are already local.
			if pkg.local:
				continue

			yield pkg

	def install(self, pkg, dep=False):
		logging.info(" --> Marking package for install: %s" % pkg.friendly_name)

		if dep:
			self.install_deps.append(pkg)
		else:
			self.installs.append(pkg)

	def remove(self, pkg, dep=False):
		logging.info(" --> Marking package for remove: %s" % pkg.friendly_name)

		if dep:
			self.remove_deps.append(pkg)
		else:
			self.removes.append(pkg)

	def update(self, pkg, dep=False):
		assert pkg.old_package

		logging.info(" --> Marking package for update: %s (was %s)" % \
			(pkg.friendly_name, pkg.old_package.friendly_version))

		if dep:
			self.update_deps.append(pkg)
		else:
			self.updates.append(pkg)

	def download(self):
		"""
			Convert all packages to BinaryPackage.
		"""
		pkgs = []
		for pkg in self.downloads:
			pkgs.append(pkg)

		# If there are no packages to download skip the rest.
		if not pkgs:
			return

		logging.info("Downloading packages:")
		i = 0
		for download in pkgs:
			i += 1
			pkg = download.download(text="(%2d/%02d): " % (i, len(pkgs)))

			for download_list in self.download_lists:
				if download in download_list:
					download_list.remove(download)
					download_list.append(pkg)
					break

		# Just an empty line to seperate the downloads from the extractions.
		logging.info("")


class Transaction(object):
	def __init__(self, pakfire, ds):
		self.pakfire = pakfire
		self.ds = ds

		self._actions = []

	def _install_pkg(self, pkg):
		assert isinstance(pkg, packages.BinaryPackage)

		# XXX add dependencies for running the script here
		action_prein   = ActionScriptPreIn(self.pakfire, pkg)

		action_install = ActionInstall(self.pakfire, pkg, deps=[action_prein])

		# XXX add dependencies for running the script here
		action_postin  = ActionScriptPostIn(self.pakfire, pkg, deps=[action_install])

		for action in (action_prein, action_install, action_postin):
			self.add_action(action)

	def _update_pkg(self, pkg):
		assert isinstance(pkg, packages.BinaryPackage)

		action_update = ActionUpdate(self.pakfire, pkg)

		action_cleanup  = ActionCleanup(self.pakfire, pkg, deps=[action_update])

		for action in (action_update, action_cleanup):
			self.add_action(action)

	def _remove_pkg(self, pkg):
		# XXX add scripts
		action_remove = ActionRemove(self.pakfire, pkg)

		for action in (action_remove):
			self.add_action(action)

	def populate(self):
		# Determine which packages we have to add
		# and which we have to remove.

		# Add all packages that need to be installed.
		for pkg in self.ds.ts.installs + self.ds.ts.install_deps:
			self._install_pkg(pkg)

		# Add all packages that need to be updated.
		for pkg in self.ds.ts.updates + self.ds.ts.update_deps:
			self._update_pkg(pkg)

		# Add all packages that need to be removed.
		for pkg in self.ds.ts.removes + self.ds.ts.remove_deps:
			self._remove_pkg(pkg)

	def add_action(self, action):
		logging.debug("New action added: %s" % action)

		self._actions.append(action)

	def remove_action(self, action):
		logging.debug("Removing action: %s" % action)

		self._actions.remove(action)
		for _action in self.actions:
			_action.remove_dep(action)

	@property
	def actions(self):
		for action in self._actions:
			yield action

	@property
	def packages(self):
		for action in self._actions:
			yield action.pkg

	def run_action(self, action):
		try:
			action.run()
		except ActionError, e:
			logging.error("Action finished with an error: %s - %s" % (action, e))

	def run(self):
		# Download all packages.
		self.ds.ts.download()

		# Create all the actions that need to be done.
		self.populate()

		while True:
			if not [a for a in self.actions]:
				break

			for action in self.actions:
				if action.deps:
					#logging.debug("Skipping %s which cannot be run now." % action)
					continue

				self.run_action(action)
				self.remove_action(action)

