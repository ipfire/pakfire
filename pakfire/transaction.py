#!/usr/bin/python

import logging

import depsolve
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
		virtpkg = self.local.db.add_package(self.pkg, installed=False)

		# Grab an instance of the extractor and set it up
		extractor = self.pkg.get_extractor(self.pakfire)

		# Extract all files to instroot
		extractor.extractall(self.pakfire.path, callback=virtpkg.add_file)

		# Mark package as installed
		virtpkg.set_installed(True)
		#self.db.commit()

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
	def __init__(self, pakfire, ds):
		self.pakfire = pakfire
		self.ds = ds

		self._actions = []

		self._installs = []
		self._removes = []
		self._updates = []

		# Reference to local repository
		self.local = pakfire.repos.local

		self._packages = self.local.get_all()

		self.populate()

	def _install_pkg(self, pkg):
		# XXX add dependencies for running the script here
		action_prein   = ActionScriptPreIn(self.pakfire, pkg)

		action_extract = ActionExtract(self.pakfire, pkg, deps=[action_prein])

		# XXX add dependencies for running the script here
		action_postin  = ActionScriptPostIn(self.pakfire, pkg, deps=[action_extract])

		for action in (action_prein, action_extract, action_postin):
			self.add_action(action)

		self._installs.append(pkg)

	def _update_pkg(self, pkg):
		action_extract = ActionExtract(self.pakfire, pkg)

		self.add_action(action_extract)
		self._updates.append(pkg)

	def _remove_pkg(self, pkg):
		# XXX TBD
		self._removes.append(pkg)

	def populate(self):
		# XXX need to check later, if this really works

		# Determine which packages we have to add
		# and which we have to remove.

		for pkg in self.ds.packages:
			pkgs = self.local.get_by_name(pkg.name)
			pkgs = [p for p in pkgs]
			if not pkgs:
				# Got a new package to install
				self._install_pkg(pkg)

			else:
				# Check for updates
				for _pkg in pkgs:
					if pkg > _pkg:
						self._update_pkg(pkg)
						break

		for pkg in self._packages:
			if not pkg in self.ds.packages:
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
	def installs(self):
		return sorted(self._installs)

	@property
	def updates(self):
		return sorted(self._updates)

	@property
	def removes(self):
		return sorted(self._removes)

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
		while True:
			if not [a for a in self.actions]:
				break

			for action in self.actions:
				if action.deps:
					#logging.debug("Skipping %s which cannot be run now." % action)
					continue

				self.run_action(action)
				self.remove_action(action)

	def dump_pkg(self, format, pkg):
		return format % (
			pkg.name,
			pkg.arch,
			pkg.friendly_version,
			pkg.repo,
			util.format_size(pkg.size),
		)

	def dump(self):
		width = 80
		line = "=" * width
		format = " %-22s %-13s %-21s %-14s %4s "

		s = []
		s.append(line)
		s.append(format % (_("Package"), _("Arch"), _("Version"), _("Repository"), _("Size")))
		s.append(line)

		if self.installs:
			s.append(_("Installing:"))
			for pkg in self.installs:
				s.append(self.dump_pkg(format, pkg))
			s.append("")

		if self.updates:
			s.append(_("Updating:"))
			for pkg in self.updates:
				s.append(self.dump_pkg(format, pkg))
			s.append("")

		if self.removes:
			s.append(_("Removing:"))
			for pkg in self.removes:
				s.append(self.dump_pkg(format, pkg))
			s.append("")

		s.append(_("Transaction Summary"))
		s.append(line)
		
		format = "%-20s %-4d %s"
		
		if self.installs:
			s.append(format % (_("Install"), len(self.installs), _("Package(s)")))
		
		if self.updates:
			s.append(format % (_("Updates"), len(self.updates), _("Package(s)")))
		
		if self.removes:
			s.append(format % (_("Remove"), len(self.removes), _("Package(s)")))

		download_size = sum([p.size for p in self.installs + self.updates])
		s.append(_("Total download size: %s") % util.format_size(download_size))
		s.append("")

		print "\n".join(s)
