#!/usr/bin/python

import logging

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


class ActionExtract(Action):
	def run(self):
		logging.debug("Extracting package %s" % self.pkg.friendly_name)

		# Create package in the database
		virtpkg = self.local.index.add_package(self.pkg)

		# Grab an instance of the extractor and set it up
		extractor = self.pkg.get_extractor(self.pakfire)

		# Extract all files to instroot
		extractor.extractall(self.pakfire.path)

		# Remove all temporary files
		extractor.cleanup()


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
	pass


class ActionRemove(Action):
	pass


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
		logging.info(" --> Marking package for update: %s" % pkg.friendly_name)

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

		action_extract = ActionExtract(self.pakfire, pkg, deps=[action_prein])

		# XXX add dependencies for running the script here
		action_postin  = ActionScriptPostIn(self.pakfire, pkg, deps=[action_extract])

		for action in (action_prein, action_extract, action_postin):
			self.add_action(action)

	def _update_pkg(self, pkg):
		assert isinstance(pkg, packages.BinaryPackage)

		action_extract = ActionExtract(self.pakfire, pkg)

		self.add_action(action_extract)

	def _remove_pkg(self, pkg):
		# XXX TBD
		pass

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

