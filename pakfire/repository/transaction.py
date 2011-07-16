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
	def __init__(self, pakfire, pkg):
		self.pakfire = pakfire
		self.pkg = pkg

		# Try to get the binary version of the package from the cache if
		# any.
		binary_package = self.pkg.get_from_cache()
		if binary_package:
			self.pkg = binary_package

	def __cmp__(self, other):
		# XXX ugly
		return cmp(self.__repr__(), other.__repr__())

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.pkg.friendly_name)

	@property
	def needs_download(self):
		return self.type in ("install", "reinstall", "upgrade", "downgrade",) \
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

		# Create package in the database
		self.local.add_package(self.pkg)

		if prefix is None:
			prefix = self.pakfire.path

		self.pkg.extract(message, prefix=prefix)

	def run(self):
		msg = _("Extracting: %s")

		if self.type == "install":
			msg = _("Installing: %s")
		elif self.type == "reinstall":
			msg = _("Reinstalling: %s")
		elif self.type == "upgrade":
			msg = _("Updating: %s")
		elif self.type == "downgrade":
			msg = _("Downgrading: %s")

		self.extract(msg % self.pkg.name)


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


class ActionChange(Action):
	type = "change"

	def run(self):
		print "XXX Change: %s" % self.pkg


class Transaction(object):
	action_classes = [
		ActionInstall,
		ActionUpdate,
		ActionRemove,
		ActionCleanup,
		ActionReinstall,
		ActionDowngrade,
		ActionChange,
	]

	def __init__(self, pakfire):
		self.pakfire = pakfire
		self.actions = []

	@classmethod
	def from_solver(cls, pakfire, solver, _transaction):
		# Create a new instance of our own transaction class.
		transaction = cls(pakfire)

		for step in _transaction.steps():
			action = step.get_type()
			pkg = packages.SolvPackage(pakfire, step.get_solvable())

			for action_cls in cls.action_classes:
				if action_cls.type == action:
					action = action_cls(pakfire, pkg)

			if not isinstance(action, Action):
				raise Exception, "Unknown action required: %s" % action

			transaction.actions.append(action)

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
		s.append(PKG_DUMP_FORMAT % (_("Package"), _("Arch"), _("Version"),
			_("Repository"), _("Size")))
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

		for caption, pkgs in actions:
			if not len(pkgs):
				continue
			s.append("%-20s %-4d %s" % (caption, len(pkgs),
				_("package", "packages", len(pkgs))))

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

	def run(self):
		# Download all packages.
		self.download()

		# Run all actions in order and catch all kinds of ActionError.
		for action in self.actions:
			try:
				action.run()
			except ActionError, e:
				logging.error("Action finished with an error: %s - %s" % (action, e))
