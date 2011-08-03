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


class ActionScript(Action):
	type = "script"

	def run(self):
		#print "Pretending to run script: %s" % self.__class__.__name__
		pass


class ActionScriptPreIn(ActionScript):
	pass


class ActionScriptPostIn(ActionScript):
	pass


class ActionScriptPreUn(ActionScript):
	pass


class ActionScriptPostUn(ActionScript):
	pass


class ActionScriptPreUp(ActionScript):
	pass


class ActionScriptPostUp(ActionScript):
	pass


class ActionScriptPostTrans(ActionScript):
	pass


class ActionScriptPostTransIn(ActionScriptPostTrans):
	pass


class ActionScriptPostTransUn(ActionScriptPostTrans):
	pass


class ActionScriptPostTransUp(ActionScriptPostTrans):
	pass


class ActionInstall(Action):
	type = "install"

	def run(self):
		# Add package to the database.
		self.local.add_package(self.pkg)

		self.pkg.extract(_("Installing"), prefix=self.pakfire.path)


class ActionUpdate(Action):
	type = "upgrade"

	def run(self):
		# Add new package to the database.
		self.local.add_package(self.pkg)

		self.pkg.extract(_("Updating"), prefix=self.pakfire.path)


class ActionRemove(Action):
	type = "erase"

	def __init__(self, *args, **kwargs):
		Action.__init__(self, *args, **kwargs)

		# XXX This is ugly, but works for the moment.
		self.pkg = self.local.index.db.get_package_from_solv(self.pkg_solv)
		assert self.pkg

	def run(self):
		self.pkg.remove(_("Removing"), prefix=self.pakfire.path)

		# Remove package from the database.
		self.local.rem_package(self.pkg)


class ActionCleanup(Action):
	type = "ignore"

	def __init__(self, *args, **kwargs):
		Action.__init__(self, *args, **kwargs)

		# XXX This is ugly, but works for the moment.
		self.pkg = self.local.index.db.get_package_from_solv(self.pkg_solv)
		assert self.pkg

	def run(self):
		# Cleaning up leftover files and stuff.
		self.pkg.cleanup(_("Cleanup"), prefix=self.pakfire.path)

		# Remove package from the database.
		self.local.rem_package(self.pkg)


class ActionReinstall(Action):
	type = "reinstall"

	def run(self):
		# Remove package from the database and add it afterwards.
		# Sounds weird, but fixes broken entries in the database.
		self.local.rem_package(self.pkg)
		self.local.add_package(self.pkg)

		self.pkg.extract(_("Installing"), prefix=self.pakfire.path)


class ActionDowngrade(Action):
	type = "downgrade"

	def run(self):
		# Add new package to database.
		self.local.add_package(self.pkg)

		self.pkg.extract(_("Downgrading"), prefix=self.pakfire.path)


class ActionChange(Action):
	type = "change"

	# XXX still need to find out what this should be doing

	def run(self):
		print "XXX Change: %s" % self.pkg
