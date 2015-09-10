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

import os
import sys

import packages
import shell
import util

import logging
log = logging.getLogger("pakfire")

from constants import *
from i18n import _

class Action(object):
	def __init__(self, pakfire, pkg_solv, pkg_bin=None):
		self.pakfire = pakfire

		self.pkg_solv = pkg_solv
		if pkg_bin:
			self.pkg_bin = pkg_bin

		self.init()

	def __cmp__(self, other):
		return cmp(self.pkg, other.pkg)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.pkg.friendly_name)

	def init(self):
		# A function to run additional initialization.
		pass

	def check(self, filelist):
		# This is just a dummy test that does nothing at all.
		return filelist

	def verify(self):
		assert self.pkg, "No package! %s" % self.pkg
		assert self.pkg.repo, "Package has no repository? %s" % self.pkg

		# Local packages need no verification.
		if self.pkg.repo.local:
			return

		# Check if there are any signatures at all.
		if not self.pkg.signatures:
			raise SignatureError, _("%s has got no signatures") % self.pkg.friendly_name

		# Run the verification process and save the result.
		sigs = self.pkg.verify()

		if not sigs:
			raise SignatureError, _("%s has got no valid signatures") % self.pkg.friendly_name

	@property
	def pkg(self):
		"""
			Return the best version of the package we can use.
		"""
		return self.pkg_bin or self.pkg_solv

	def get_binary_package(self):
		"""
			Tries to find the binary version of the package in the local cache.
		"""
		return self.pkg_solv.get_from_cache()

	def _get_pkg_bin(self):
		if not hasattr(self, "_pkg_bin"):
			self._pkg_bin = self.get_binary_package()

		return self._pkg_bin

	def _set_pkg_bin(self, pkg):
		if pkg and not self.pkg_solv.uuid == pkg.uuid:
			raise RuntimeError, "Not the same package: %s != %s" % (self.pkg_solv, pkg)

		self._pkg_bin = pkg

	pkg_bin = property(_get_pkg_bin, _set_pkg_bin)

	def run(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Reference to local repository.
		"""
		return self.pakfire.repos.local

	def get_logger_name(self):
		return "pakfire.action.%s" % self.pkg.friendly_name

	def get_logger(self):
		logger_name = self.get_logger_name()

		logger = logging.getLogger(logger_name)
		logger.setLevel(logging.INFO)

		# Propagate everything to upstream logger.
		logger.propagate = True

		return logger

	def execute(self, command, **kwargs):
		# If we are running in /, we do not need to chroot there.
		chroot_path = None
		if not self.pakfire.path == "/":
			chroot_path = self.pakfire.path

		# Find suitable cwd.
		cwd = "/"
		for i in ("tmp", "root"):
			if chroot_path:
				_cwd = os.path.join(chroot_path, i)
			else:
				_cwd = i

			if os.path.exists(_cwd):
				cwd = _cwd
				break

		args = {
			"cwd"         : cwd,
			"env"         : {
				"LANG" : "C",
				"PATH" : "/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin",
			},
			"logger"      : self.get_logger(),
			"personality" : self.pakfire.distro.personality,
			"shell"       : False,
			"timeout"     : SCRIPTLET_TIMEOUT,
		}

		# Overwrite by args that were passed.
		args.update(kwargs)

		# You can never overwrite chrootPath.
		args["chroot_path"] = chroot_path

		# Execute command.
		shellenv = shell.ShellExecuteEnvironment(command, **args)
		shellenv.execute()


class ActionScript(Action):
	type = "script"
	script_action = None

	def init(self):
		self._scriptlet = None

	def get_logger_name(self):
		logger_name = Action.get_logger_name(self)

		return "%s.%s" % (logger_name, self.script_action or "unknown")

	@property
	def scriptlet(self):
		"""
			Load the scriplet.
		"""
		if self._scriptlet is None:
			self._scriptlet = self.pkg.get_scriptlet(self.script_action)

		return self._scriptlet

	def get_lang(self):
		if not self.scriptlet:
			return

		interp = None

		for line in self.scriptlet.splitlines():
			if line.startswith("#!/"):
				interp = "exec"
				break

			elif line.startswith("#<lang: "):
				interp = line[8:].replace(">", "")
				break

		return interp

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
		log.debug("Running scriptlet %s" % self)

		# Check of what kind the scriptlet is and run the
		# corresponding handler.
		lang = self.get_lang()

		if lang == "exec":
			self.run_exec()

		elif lang == "python":
			self.run_python()

		else:
			raise ActionError, _("Could not handle scriptlet of unknown type. Skipping.")

	def run_exec(self):
		log.debug(_("Executing scriptlet..."))

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
		assert script_file.startswith(self.pakfire.path)

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

		try:
			self.execute(command)

		except ShellEnvironmentError, e:
			raise ActionError, _("The scriptlet returned an error:\n%s" % e)

		except commandTimeoutExpired:
			raise ActionError, _("The scriptlet ran more than %s seconds and was killed." \
				% SCRIPTLET_TIMEOUT)

		except Exception, e:
			raise ActionError, _("The scriptlet returned with an unhandled error:\n%s" % e)

		finally:
			# Remove the script file.
			try:
				os.unlink(script_file)
			except OSError:
				log.debug("Could not remove scriptlet file: %s" % script_file)

	def run_python(self):
		# This functions creates a fork with then chroots into the
		# pakfire root if necessary and then compiles the given scriptlet
		# code and runs it.

		log.debug(_("Executing python scriptlet..."))

		# Create fork.
		pid = os.fork()

		if not pid:
			# child code

			# The child chroots into the pakfire path.
			if not self.pakfire.path == "/":
				os.chroot(self.pakfire.path)

			# Create a clean global environment, where only
			# builtin functions are available and the os and sys modules.
			_globals = {
				"os"  : os,
				"sys" : sys,
			}

			# Compile the scriptlet and execute it.
			try:
				obj = compile(self.scriptlet, "<string>", "exec")
				eval(obj, _globals, {})

			except Exception, e:
				print _("Exception occured: %s") % e
				os._exit(1)

			# End the child process without cleaning up.
			os._exit(0)

		else:
			# parent code

			# Wait until the child process has finished.
			os.waitpid(pid, 0)


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


class ActionScriptPreTrans(ActionScript):
	pass


class ActionScriptPreTransIn(ActionScriptPreTrans):
	script_action = "pretransin"


class ActionScriptPreTransUn(ActionScriptPreTrans):
	script_action = "pretransun"


class ActionScriptPreTransUp(ActionScriptPreTrans):
	script_action = "pretransup"


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

	def check(self, check):
		log.debug(_("Running transaction test for %s") % self.pkg.friendly_name)

		# Check if this package can be installed.
		check.install(self.pkg)

	def run(self):
		# Add package to the database.
		self.local.add_package(self.pkg)

		if isinstance(self, ActionReinstall):
			msg = _("Reinstalling")
		elif isinstance(self, ActionUpdate):
			msg = _("Updating")
		elif isinstance(self, ActionDowngrade):
			msg = _("Downgrading")
		else:
			msg = _("Installing")

		self.pkg.extract(msg, prefix=self.pakfire.path)

		# Check if shared objects were extracted. If this is the case, we need
		# to run ldconfig.
		ldconfig_needed = False
		for file in self.pkg.filelist:
			if ".so." in file.name:
				ldconfig_needed = True
				break

			if "etc/ld.so.conf" in file.name:
				ldconfig_needed = True
				break

		if ldconfig_needed:
			# Check if ldconfig is present.
			ldconfig = os.path.join(self.pakfire.path, LDCONFIG[1:])

			if os.path.exists(ldconfig) and os.access(ldconfig, os.X_OK):
				self.execute(LDCONFIG)

			else:
				log.debug("ldconfig is not present or not executable.")


class ActionUpdate(ActionInstall):
	type = "upgrade"

	def check(self, check):
		log.debug(_("Running transaction test for %s") % self.pkg.friendly_name)

		# Check if this package can be updated.
		check.update(self.pkg)


class ActionRemove(Action):
	type = "erase"

	def check(self, check):
		log.debug(_("Running transaction test for %s") % self.pkg.friendly_name)

		# Check if this package can be removed.
		check.remove(self.pkg)

	def run(self):
		if isinstance(self, ActionCleanup):
			msg = _("Cleanup")
		else:
			msg = _("Removing")

		self.pkg.cleanup(msg, prefix=self.pakfire.path)

		# Remove package from the database.
		self.local.rem_package(self.pkg)


class ActionCleanup(ActionRemove):
	type = "ignore"

	def check(self, check):
		log.debug(_("Running transaction test for %s") % self.pkg.friendly_name)

		# Check if this package can be removed.
		check.cleanup(self.pkg)


class ActionReinstall(ActionInstall):
	type = "reinstall"


class ActionDowngrade(ActionInstall):
	type = "downgrade"
