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

import logging
import os

import chroot
import packages
import util

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

		self.init()

	def __cmp__(self, other):
		return cmp(self.pkg, other.pkg)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.pkg.friendly_name)

	def init(self):
		# A function to run additional initialization.
		pass

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
	script_action = None

	def init(self):
		# Load the scriplet.
		self.scriptlet = self.pkg.get_scriptlet(self.script_action)

	@property
	def interpreter(self):
		"""
			Get the interpreter of this scriptlet.
		"""
		return util.scriptlet_interpreter(self.scriptlet)

	@property
	def args(self):
		return []

	def run(self):
		# Exit immediately, if the scriptlet is empty.
		if not self.scriptlet:
			return

		# Actually run the scriplet.
		logging.debug("Running scriptlet %s" % self)

		# Check if the interpreter does exist and is executable.
		if self.interpreter:
			interpreter = "%s/%s" % (self.pakfire.path, self.interpreter)
			if not os.path.exists(interpreter):
				raise ActionError, _("Cannot run scriptlet because no interpreter is available: %s" \
					% self.interpreter)

			if not os.access(interpreter, os.X_OK):
				raise ActionError, _("Cannot run scriptlet because the interpreter is not executable: %s" \
					% self.interpreter)

		# Create a name for the temporary script file.
		script_file_chroot = os.path.join("/", LOCAL_TMP_PATH,
			"scriptlet_%s" % util.random_string(10))
		script_file = os.path.join(self.pakfire.path, script_file_chroot[1:])
		assert script_file.startswith("%s/" % self.pakfire.path)

		# Create script directory, if it does not exist.
		script_dir = os.path.dirname(script_file)
		if not os.path.exists(script_dir):
			os.makedirs(script_dir)

		# Write the scriptlet to a file that we can execute it.
		try:
			f = open(script_file, "wb")
			f.write(self.scriptlet)
			f.close()

			# The file is only accessable by root.
			os.chmod(script_file, 700)
		except:
			# Remove the file if an error occurs.
			try:
				os.unlink(script_file)
			except OSError:
				pass

			# XXX catch errors and return a beautiful message to the user
			raise

		# Generate the script command.
		command = [script_file_chroot] + self.args

		# If we are running in /, we do not need to chroot there.
		chroot_path = None
		if not self.pakfire.path == "/":
			chroot_path = self.pakfire.path

		try:
			ret = chroot.do(command, cwd="/tmp",
				chrootPath=chroot_path,
				personality=self.pakfire.distro.personality,
				shell=False,
				timeout=SCRIPTLET_TIMEOUT,
				logger=logging.getLogger())

		except Error, e:
			raise ActionError, _("The scriptlet returned an error:\n%s" % e)

		except commandTimeoutExpired:
			raise ActionError, _("The scriptlet ran more than %s seconds and was killed." \
				% SCRIPTLET_TIMEOUT)

		finally:
			# Remove the script file.
			try:
				os.unlink(script_file)
			except OSError:
				logging.debug("Could not remove scriptlet file: %s" % script_file)


class ActionScriptPreIn(ActionScript):
	script_action = "prein"


class ActionScriptPostIn(ActionScript):
	script_action = "postin"


class ActionScriptPreUn(ActionScript):
	script_action = "preun"


class ActionScriptPostUn(ActionScript):
	script_action = "postun"


class ActionScriptPreUp(ActionScript):
	script_action = "preup"


class ActionScriptPostUp(ActionScript):
	script_action = "postup"


class ActionScriptPostTrans(ActionScript):
	pass


class ActionScriptPostTransIn(ActionScriptPostTrans):
	script_action = "posttransin"


class ActionScriptPostTransUn(ActionScriptPostTrans):
	script_action = "posttransun"


class ActionScriptPostTransUp(ActionScriptPostTrans):
	script_action = "posttransup"


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
		self.pkg.cleanup(_("Removing"), prefix=self.pakfire.path)

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
