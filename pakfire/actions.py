#!/usr/bin/python

import logging

import packages

from constants import *
from i18n import _

class Action(object):
	def __init__(self, pakfire, pkg):
		self.pakfire = pakfire
		self.pkg_solv = self.pkg = pkg

		# Try to get the binary version of the package from the cache if
		# any.
		binary_package = self.pkg.get_from_cache()
		if binary_package:
			self.pkg = binary_package

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


class ActionRemove(Action):
	type = "erase"

	def __init__(self, *args, **kwargs):
		Action.__init__(self, *args, **kwargs)

		# XXX This is ugly, but works for the moment.
		self.pkg = self.local.index.db.get_package_from_solv(self.pkg_solv)
		assert self.pkg

	def run(self):
		self.pkg.remove(_("Removing"), prefix=self.pakfire.path)

		# XXX Remove package from database


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
