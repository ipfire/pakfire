#!/usr/bin/python

import logging
import os
import progressbar
import satsolver
import sys

import pakfire.packages as packages
import pakfire.util as util

from pakfire.i18n import _

PKG_DUMP_FORMAT = " %-21s %-8s %-21s %-19s %5s "

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

	@property
	def needs_download(self):
		return self.type in ("install", "reinstall", "update", "downgrade",) \
			and not isinstance(self.pkg, packages.BinaryPackage)

	def download(self, text):
		if not self.needs_download:
			return

		self.pkg = self.pkg.download(text)

	def run(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Reference to local repository (database).
		"""
		return self.pakfire.repos.local


class ActionCleanup(Action):
	type = "ignore"

	def run(self):
		print "XXX Cleanup: %s" % self.pkg


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
	type = "install"

	def extract(self, message, prefix=None):
		logging.debug("Extracting package %s" % self.pkg.friendly_name)

		if prefix is None:
			prefix = self.pakfire.path

		self.pkg.extract(message, prefix=prefix)

		# Create package in the database
		self.local.index.add_package(self.pkg)

	def run(self):
		msg = _("Extracting: %s")

		if self.type == "install":
			msg = _("Installing: %s")
		elif self.type == "reinstall":
			msg = _("Reinstalling: %s")
		elif self.type == "update":
			msg = _("Updating: %s")
		elif self.type == "downgrade":
			msg = _("Downgrading: %s")

		self.extract(msg % self.pkg.name)

		self.pakfire.solver.add_package(self.pkg, "installed")


class ActionUpdate(ActionInstall):
	type = "upgrade"

class ActionRemove(ActionCleanup):
	type = "erase"

	def run(self):
		files = self.pkg.filelist

		if not files:
			return

		self.remove_files(_("Removing: %s") % self.pkg.name, files)


class ActionReinstall(ActionInstall):
	type = "reinstall"


class ActionDowngrade(ActionInstall):
	type = "downgrade"


class Transaction(object):
	action_classes = [
		ActionInstall,
		ActionUpdate,
		ActionRemove,
		ActionCleanup,
		ActionReinstall,
		ActionDowngrade,
	]

	def __init__(self, pakfire):
		self.pakfire = pakfire
		self.actions = []

	@classmethod
	def from_solver(cls, pakfire, solver1, solver2):
		# Grab the original transaction object from the solver.
		_transaction = solver2.transaction()

		# Order the objects in the transaction in that way we will run the
		# installation.
		_transaction.order()

		# Create a new instance of our own transaction class.
		transaction = cls(pakfire)

		for step in _transaction.steps():
			action = step.type_s(satsolver.TRANSACTION_MODE_ACTIVE)
			pkg = solver1.solv2pkg(step.solvable())

			if action in ("install", "reinstall", "upgrade") and \
					not isinstance(pkg, packages.BinaryPackage):
				transaction.downloads.append(pkg)

			for action_cls in cls.action_classes:
				if action_cls.type == action:
					action = action_cls(pakfire, pkg)

			if not isinstance(action, Action):
				raise Exception, "Unknown action required: %s" % action

			transaction.add_action(action)

		print transaction.actions
		return transaction

	@property
	def installs(self):
		return [a.pkg for a in self.actions if isinstance(a, ActionInstall)]

	@property
	def reinstalls(self):
		return [a.pkg for a in self.actions if isinstance(a, ActionReinstall)]

	@property
	def removes(self):
		return [a.pkg for a in self.actions if isinstance(a, ActionRemove)]

	@property
	def updates(self):
		return [a.pkg for a in self.actions if isinstance(a, ActionUpdate)]

	@property
	def downgrades(self):
		return [a.pkg for a in self.actions if isinstance(a, ActionDowngrade)]

	@property
	def downloads(self):
		return [a for a in self.actions if a.needs_download]

	def download(self):
		downloads = self.downloads

		i = 0
		for action in self.actions:
			i += 1

			action.download(text="(%02d/%02d): " % (i, len(downloads)))

	def dump_pkg(self, pkg):
		ret = []

		name = pkg.name
		if len(name) > 21:
			ret.append(" %s" % name)
			name = ""

		ret.append(PKG_DUMP_FORMAT % (name, pkg.arch, pkg.friendly_version,
			pkg.repo.name, util.format_size(pkg.size)))

		return ret

	def dump_pkgs(self, caption, pkgs):
		if not pkgs:
			return []

		s = [caption,]
		for pkg in sorted(pkgs):
			s += self.dump_pkg(pkg)
		s.append("")
		return s

	def dump(self, logger=None):
		if not logger:
			logger = logging.getLogger()

		width = 80
		line = "=" * width

		s = [""]
		s.append(line)
		s.append(PKG_DUMP_FORMAT % (_("Package"), _("Arch"), _("Version"), _("Repository"), _("Size")))
		s.append(line)

		actions = (
			(_("Installing:"),		self.installs),
			(_("Reinstalling:"),	self.reinstalls),
			(_("Updating:"),		self.updates),
			(_("Downgrading:"),		self.downgrades),
			(_("Removing:"),		self.removes),
		)

		for caption, pkgs in actions:
			s += self.dump_pkgs(caption, pkgs)

		s.append(_("Transaction Summary"))
		s.append(line)

		format = "%-20s %-4d %s"

		for caption, pkgs in actions:
			if not len(pkgs):
				continue
			s.append(format % (caption, len(pkgs), _("package", "packages", len(pkgs))))

		# Calculate the size of all files that need to be downloaded this this
		# transaction.
		download_size = sum([a.pkg.size for a in self.downloads])
		if download_size:
			s.append(_("Total download size: %s") % util.format_size(download_size))
		s.append("")

		for line in s:
			logger.info(line)

	def cli_yesno(self, logger=None):
		self.dump(logger)

		return util.ask_user(_("Is this okay?"))

	def run_action(self, action):
		try:
			action.run()
		except ActionError, e:
			logging.error("Action finished with an error: %s - %s" % (action, e))

	def add_action(self, action):
		logging.debug("New action added: %s" % action)

		self.actions.append(action)

	def remove_action(self, action):
		logging.debug("Removing action: %s" % action)

		self.actions.remove(action)
		for action in self.actions:
			action.remove_dep(action)

	def run(self):
		# Download all packages.
		self.download()

		while True:
			if not [a for a in self.actions]:
				break

			for action in self.actions:
				if action.deps:
					#logging.debug("Skipping %s which cannot be run now." % action)
					continue

				self.run_action(action)
				self.remove_action(action)
