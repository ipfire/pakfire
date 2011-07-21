#!/usr/bin/python

import logging

import packages

from constants import *
from i18n import _

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
			Reference to local repository.
		"""
		return self.pakfire.repos.local

	def _extract(self, message, prefix=None):
		# Add package to the database.
		self.local.add_package(self.pkg)

		if prefix is None:
			prefix = self.pakfire.path

		self.pkg.extract(message, prefix=prefix)


class ActionCleanup(Action):
	type = "ignore"

	def run(self):
		print "XXX Cleanup: %s" % self.pkg


class ActionScript(Action):
	def run(self):
		pass


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

	def run(self):
		self._extract(_("Installing"))


class ActionUpdate(Action):
	type = "upgrade"

	def run(self):
		self._extract(_("Updating"))


class ActionRemove(ActionCleanup):
	type = "erase"

	def run(self):
		files = self.pkg.filelist

		if not files:
			return

		self.remove_files(_("Removing: %s") % self.pkg.name, files)


class ActionReinstall(Action):
	type = "reinstall"

	def run(self):
		self._extract(_("Installing"))


class ActionDowngrade(Action):
	type = "downgrade"

	def run(self):
		self._extract(_("Downgrading"))


class ActionChange(Action):
	type = "change"

	def run(self):
		print "XXX Change: %s" % self.pkg
