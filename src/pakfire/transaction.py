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
import progressbar
import sys
import time

import i18n
import packages
import satsolver
import system
import util
import _pakfire

import logging
log = logging.getLogger("pakfire")

from constants import *
from i18n import _

# Import all actions directly.
from actions import *

class TransactionCheck(object):
	def __init__(self, pakfire, transaction):
		self.pakfire = pakfire
		self.transaction = transaction

		# A place to store errors.
		self.errors = []

		# Get a list of all installed files from the database.
		self.filelist = self.load_filelist()

		# Get information about the mounted filesystems.
		self.mountpoints = system.Mountpoints(self.pakfire.path)

	@property
	def error_files(self):
		ret = []

		for name, count in self.filelist.items():
			if count > 1:
				ret.append(name)

		return sorted(ret)

	def provides_file(self, name):
		return [] # XXX TODO

	@property
	def successful(self):
		if self.error_files:
			return False

		# Check if all mountpoints have enough space left.
		for mp in self.mountpoints:
			if mp.space_left < 0:
				return False

		return True

	def print_errors(self, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		for file in self.error_files:
			pkgs = self.provides_file(file)

			if len(pkgs) == 2:
				logger.critical(
					_("file %(name)s from %(pkg1)s conflicts with file from package %(pkg2)s") % \
						{ "name" : file, "pkg1" : pkgs[0], "pkg2" : pkgs[1] }
				)

			elif len(pkgs) >= 3:
				logger.critical(
					_("file %(name)s from %(pkg)s conflicts with files from %(pkgs)s") % \
						{ "name" : file, "pkg" : pkgs[0], "pkgs" : i18n.list(pkgs[1:])}
				)

			else:
				logger.critical(
					_("file %(name)s causes the transaction test to fail for an unknown reason") % \
						{ "name" : file }
				)

		for mp in self.mountpoints:
			if mp.space_left >= 0:
				continue

			logger.critical(_("There is not enough space left on %(name)s. Need at least %(size)s to perform transaction.") \
				% { "name" : mp.path, "size" : util.format_size(mp.space_needed) })

	def load_filelist(self):
		filelist = {}

		for file in self.pakfire.repos.local.filelist:
			filelist[file] = 1

		return filelist

	def install(self, pkg):
		for file in pkg.filelist:
			if file.is_dir():
				continue

			try:
				self.filelist[file.name] += 1
			except KeyError:
				self.filelist[file.name] = 1

		# Add all filesize data to mountpoints.
		self.mountpoints.add_pkg(pkg)

	def remove(self, pkg):
		for file in pkg.filelist:
			if file.is_dir():
				continue

			try:
				self.filelist[file.name] -= 1
			except KeyError:
				pass

		# Remove all filesize data from mountpoints.
		self.mountpoints.rem_pkg(pkg)

	def update(self, pkg):
		self.install(pkg)

	def cleanup(self, pkg):
		self.remove(pkg)


class Step(object):
	def __init__(self, pakfire, type, pkg):
		self.pakfire = pakfire

		self.type = type
		self.pkg = pkg

	@classmethod
	def from_step(cls, pakfire, step):
		pkg = packages.SolvPackage(pakfire, step.get_solvable())

		return cls(pakfire, step.get_type(), pkg)

	def __repr__(self):
		return "<%s %s %s>" % (self.__class__.__name__, self.type, self.pkg)

	def get_binary_pkg(self):
		if not hasattr(self, "__binary_pkg"):
			if self.type in (ActionCleanup.type, ActionRemove.type):
				self.__binary_pkg = self.pkg.get_from_db()
				assert self.__binary_pkg
			else:
				self.__binary_pkg = self.pkg.get_from_cache()

		return self.__binary_pkg

	def set_binary_pkg(self, pkg):
		self.__binary_pkg = pkg

	binary_pkg = property(get_binary_pkg, set_binary_pkg)

	@property
	def needs_download(self):
		"""
			Returns True if the package file needs to be downloaded.
		"""
		if not self.type in (ActionInstall.type, ActionReinstall.type,
				ActionUpdate.type, ActionDowngrade.type):
			return False

		# If no binary version of the package has been found,
		# we don't need to download anything
		return not self.binary_pkg

	def create_actions(self):
		actions = []

		for action_cls in Transaction.action_classes.get(self.type, []):
			action = action_cls(self.pakfire, self.pkg, self.binary_pkg)
			actions.append(action)

		return actions


class Transaction(object):
	action_classes = {
		ActionInstall.type : [
			ActionScriptPreTransIn,
			ActionScriptPreIn,
			ActionInstall,
			ActionScriptPostIn,
			ActionScriptPostTransIn,
		],
		ActionReinstall.type : [
			ActionScriptPreTransIn,
			ActionScriptPreIn,
			ActionReinstall,
			ActionScriptPostIn,
			ActionScriptPostTransIn,
		],
		ActionRemove.type : [
			ActionScriptPreTransUn,
			ActionScriptPreUn,
			ActionRemove,
			ActionScriptPostUn,
			ActionScriptPostTransUn,
		],
		ActionUpdate.type : [
			ActionScriptPreTransUp,
			ActionScriptPreUp,
			ActionUpdate,
			ActionScriptPostUp,
			ActionScriptPostTransUp,
		],
		ActionCleanup.type : [
			ActionCleanup,
		],
		ActionDowngrade.type : [
			ActionScriptPreTransUp,
			ActionScriptPreUp,
			ActionDowngrade,
			ActionScriptPostUp,
			ActionScriptPostTransUp,
		],
	}

	def __init__(self, pakfire):
		self.pakfire = pakfire

		self._steps = []
		self.installsizechange = 0

	def __nonzero__(self):
		if self.steps:
			return True

		return False

	@classmethod
	def from_solver(cls, pakfire, solver):
		# Create a new instance of our own transaction class.
		transaction = cls(pakfire)

		# Get transaction data from the solver.
		_transaction = _pakfire.Transaction(solver.solver)

		# Save installsizechange.
		transaction.installsizechange = _transaction.get_installsizechange()

		# Get all steps that need to be done from the solver.
		for step in _transaction.steps():
			step = Step.from_step(pakfire, step)
			transaction.add_step(step)

		return transaction

	@property
	def local(self):
		# Shortcut to local repository.
		return self.pakfire.repos.local

	@property
	def steps(self):
		return self._steps

	def add_step(self, step):
		"""
			Adds a new step to this transaction.
		"""
		assert isinstance(step, Step), step

		self._steps.append(step)

	def get_steps_by_type(self, type):
		return [s for s in self.steps if s.type == type]

	@property
	def installs(self):
		return self.get_steps_by_type(ActionInstall.type)

	@property
	def reinstalls(self):
		return self.get_steps_by_type(ActionReinstall.type)

	@property
	def removes(self):
		return self.get_steps_by_type(ActionRemove.type)

	@property
	def updates(self):
		return self.get_steps_by_type(ActionUpdate.type)

	@property
	def downgrades(self):
		return self.get_steps_by_type(ActionDowngrade.type)

	def get_downloads(self):
		"""
			Returns a list of all steps that need
			to a download.
		"""
		return [s for s in self.steps if s.needs_download]

	@property
	def download_size(self):
		"""
			Returns the amount of bytes that need to be downloaded.
		"""
		if not hasattr(self, "__download_size"):
			self.__download_size = sum((s.pkg.size for s in self.get_downloads()))

		return self.__download_size

	def download(self, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		downloads = self.get_downloads()

		# If there are no downloads, we can just stop here.
		if not downloads:
			return

		# Get free space of the download location.
		path = os.path.realpath(REPO_CACHE_DIR)
		while not os.path.ismount(path):
			path = os.path.dirname(path)
		path_stat = os.statvfs(path)

		if self.download_size >= path_stat.f_bavail * path_stat.f_bsize:
			raise DownloadError, _("Not enough space to download %s of packages.") \
				% util.format_size(self.download_size)

		logger.info(_("Downloading packages:"))
		time_start = time.time()

		counter = 0
		counter_downloads = len(downloads)
		for step in downloads:
			counter += 1

			# Download the package file.
			step.binary_pkg = step.pkg.download(
				text="(%d/%d): " % (counter, counter_downloads),
				logger=logger)

		# Write an empty line to the console when there have been any downloads.
		width, height = util.terminal_size()

		# Print a nice line.
		logger.info("-" * width)

		# Format and calculate download information.
		time_stop = time.time()
		download_time = time_stop - time_start
		download_speed = self.download_size / download_time
		download_speed = util.format_speed(download_speed)
		download_size = util.format_size(self.download_size)
		download_time = util.format_time(download_time)

		line = "%s | %5sB     %s     " % \
			(download_speed, self.download_size, download_time)
		line = " " * (width - len(line)) + line
		logger.info(line)
		logger.info("")

	def print_section(self, caption, steps, format_string):
		section = [caption,]

		pkgs = [s.pkg for s in steps]
		for pkg in sorted(pkgs):
			line = format_string % {
				"arch"     : pkg.arch,
				"name"     : pkg.name,
				"repo"     : pkg.repo.name,
				"size"     : util.format_size(pkg.size),
				"version"  : pkg.friendly_version,
			}
			section.append(line)

		section.append("")

		return section

	def dump(self, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		if not self.steps:
			logger.info(_("Nothing to do"))
			return

		# Prepare some string formatting stuff.
		# XXX this needs to adapt to the terminal size
		format_string = " %(name)-21s %(arch)-8s %(version)-21s %(repo)-18s %(size)6s "

		# Prepare the headline.
		headline = format_string % {
			"arch"    : _("Arch"),
			"name"    : _("Package"),
			"repo"    : _("Repository"),
			"size"    : _("Size"),
			"version" : _("Version"),
		}

		# As long, as we can't use the actual terminal width, we use the
		# length of the headline.
		terminal_width = len(headline)

		# Create a separator line.
		sep_line = "=" * terminal_width

		# Create the header.
		s = [sep_line, headline, sep_line,]

		steps = (
			(_("Installing:"),   self.installs),
			(_("Reinstalling:"), self.reinstalls),
			(_("Updating:"),     self.updates),
			(_("Downgrading:"),  self.downgrades),
			(_("Removing:"),     self.removes),
		)

		for caption, _steps in steps:
			if not _steps:
				continue

			s += self.print_section(caption, _steps, format_string)

		# Append the transaction summary
		s.append(_("Transaction Summary"))
		s.append(sep_line)

		for caption, _steps in steps:
			if not _steps:
				continue

			s.append("%-20s %-4d %s" % (caption, len(_steps),
				_("package", "packages", len(_steps))))

		# Calculate the size of all files that need to be downloaded this this
		# transaction.
		if self.download_size:
			s.append(_("Total download size: %s") % util.format_size(self.download_size))

		# Show the size that is consumed by the new packages.
		if self.installsizechange > 0:
			s.append(_("Installed size: %s") % util.format_size(self.installsizechange))
		elif self.installsizechange < 0:
			s.append(_("Freed size: %s") % util.format_size(-self.installsizechange))
		s.append("")

		for line in s:
			logger.info(line)

	def cli_yesno(self):
		# Empty transactions are always denied.
		if not self.steps:
			return False

		return util.ask_user(_("Is this okay?"))

	def check(self, actions, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		logger.info(_("Running Transaction Test"))

		# Initialize the check object.
		check = TransactionCheck(self.pakfire, self)

		for action in actions:
			try:
				action.check(check)
			except ActionError, e:
				raise

		if check.successful:
			logger.info(_("Transaction Test Succeeded"))
			return

		# In case of an unsuccessful transaction test, we print the error
		# and raise TransactionCheckError.
		check.print_errors(logger=logger)

		raise TransactionCheckError, _("Transaction test was not successful")

	def verify_signatures(self, mode=None, logger=None):
		"""
			Check the downloaded files for valid signatures.
		"""
		if not logger:
			logger = log.getLogger("pakfire")

		if mode is None:
			mode = self.pakfire.config.get("signatures", "mode", "strict")

		# If this disabled, we do nothing.
		if mode == "disabled":
			return

		# Search for steps we need to process.
		steps = []
		for step in self.steps:
			if not step.binary_pkg:
				continue

			steps.append(step)

		# Make a nice progressbar.
		p = progressbar.ProgressBar(len(steps))
		p.add(_("Verifying signatures..."))
		p.add(progressbar.WidgetBar())
		p.add(progressbar.WidgetPercentage())

		# Collect all errors.
		errors = []

		try:
			p.start()

			# Do the verification for every action.
			i = 0
			for step in steps:
				# Update the progressbar.
				if p:
					i += 1
					p.update(i)

				try:
					step.pkg.verify()

				except SignatureError, e:
					errors.append("%s" % e)
		finally:
			if p: p.finish()

		# If no errors were found everything is fine.
		if not errors:
			logger.info("")
			return

		# Raise a SignatureError in strict mode.
		if mode == "strict":
			raise SignatureError, "\n".join(errors)

		elif mode == "permissive":
			logger.warning(_("Found %s signature error(s)!") % len(errors))
			for error in errors:
				logger.warning("  %s" % error)
			logger.warning("")

			logger.warning(_("Going on because we are running in permissive mode."))
			logger.warning(_("This is dangerous!"))
			logger.warning("")

	def create_actions(self):
		"""
			Create actions from steps.
		"""
		actions = []
		actions_pre = []
		actions_post = []

		for step in self.steps:
			for action in step.create_actions():
				if isinstance(action, ActionScriptPreTrans):
					actions_pre.append(action)
				elif isinstance(action, ActionScriptPostTrans):
					actions_post.append(action)
				else:
					actions.append(action)

		return actions_pre + actions + actions_post

	def run(self, logger=None, signatures_mode=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		# Download all packages.
		# (don't add logger here because I do not want to see downloads
		# in the build logs on the build service)
		self.download()

		# Verify signatures.
		#self.verify_signatures(mode=signatures_mode, logger=logger)

		# Create actions.
		actions = self.create_actions()

		# Run the transaction test
		self.check(actions, logger=logger)

		logger.info(_("Running transaction"))
		# Run all actions in order and catch all kinds of ActionError.
		for action in actions:
			try:
				action.run()

			except ActionError, e:
				logger.error("Action finished with an error: %s - %s" % (action, e))
			#except Exception, e:
			#	logger.error(_("An unforeseen error occoured: %s") % e)

		logger.info("")

		# Commit repository metadata.
		self.local.commit()

		# Call sync to make sure all buffers are written to disk.
		_pakfire.sync()
