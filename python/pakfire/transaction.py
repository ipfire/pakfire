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

import logging
log = logging.getLogger("pakfire")

from constants import *
from i18n import _
from pakfire._pakfire import Transaction, sync
_Transaction = Transaction

PKG_DUMP_FORMAT = " %-21s %-8s %-21s %-18s %6s "

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
		ret = {}

		for name, files in self.filelist.items():
			if len(files) <= 1:
				continue

			ret[name] = files

		return ret

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

		for name, files in sorted(self.error_files.items()):
			assert len(files) >= 2

			pkgs = [f.pkg.friendly_name for f in files]

			if len(files) == 2:
				logger.critical(
					_("file %(name)s from %(pkg1)s conflicts with file from package %(pkg2)s") % \
						{ "name" : name, "pkg1" : pkgs[0], "pkg2" : pkgs[1] }
				)

			elif len(files) >= 3:
				logger.critical(
					_("file %(name)s from %(pkg)s conflicts with files from %(pkgs)s") % \
						{ "name" : name, "pkg" : pkgs[0], "pkgs" : i18n.list(pkgs[1:])}
				)

		for mp in self.mountpoints:
			if mp.space_left >= 0:
				continue

			logger.critical(_("There is not enough space left on %(name)s. Need at least %(size)s to perform transaction.") \
				% { "name" : mp.path, "size" : util.format_size(mp.space_needed) })

	def load_filelist(self):
		filelist = {}

		for file in self.pakfire.repos.local.filelist:
			filelist[file.name] = [file,]

		return filelist

	def install(self, pkg):
		for file in pkg.filelist:
			if file.is_dir():
				continue

			if self.filelist.has_key(file.name):
				self.filelist[file.name].append(file)

			else:
				self.filelist[file.name] = [file,]

		# Add all filesize data to mountpoints.
		self.mountpoints.add_pkg(pkg)

	def remove(self, pkg):
		for file in pkg.filelist:
			if file.is_dir():
				continue

			if not self.filelist.has_key(file.name):
				continue

			for f in self.filelist[file.name]:
				if not f.pkg == pkg:
					continue

				self.filelist[file.name].remove(f)

		# Remove all filesize data from mountpoints.
		self.mountpoints.rem_pkg(pkg)

	def update(self, pkg):
		self.install(pkg)

	def cleanup(self, pkg):
		self.remove(pkg)


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
		self.actions = []

		self.installsizechange = 0

		self.__need_sort = False

	def __nonzero__(self):
		if self.actions:
			return True

		return False

	@classmethod
	def from_solver(cls, pakfire, solver):
		# Create a new instance of our own transaction class.
		transaction = cls(pakfire)

		# Get transaction data from the solver.
		_transaction = _Transaction(solver.solver)

		# Save installsizechange.
		transaction.installsizechange = _transaction.get_installsizechange()

		# Get all steps that need to be done from the solver.
		steps = _transaction.steps()

		actions = []
		actions_post = []

		for step in steps:
			action_name = step.get_type()
			pkg = packages.SolvPackage(pakfire, step.get_solvable())

			transaction.add(action_name, pkg)

		# Sort all previously added actions.
		transaction.sort()

		return transaction

	@property
	def local(self):
		# Shortcut to local repository.
		return self.pakfire.repos.local

	def add(self, action_name, pkg):
		assert isinstance(pkg, packages.SolvPackage), pkg

		try:
			classes = self.action_classes[action_name]
		except KeyError:
			raise Exception, "Unknown action requires: %s" % action_name

		for cls in classes:
			action = cls(self.pakfire, pkg)
			assert isinstance(action, Action), action

			self.actions.append(action)

		self.__need_sort = True

	def sort(self):
		"""
			Sort all actions.
		"""
		actions = []
		actions_pre = []
		actions_post = []

		for action in self.actions:
			if isinstance(action, ActionScriptPreTrans):
				actions_pre.append(action)
			elif isinstance(action, ActionScriptPostTrans):
				actions_post.append(action)
			else:
				actions.append(action)

		self.actions = actions_pre + actions + actions_post
		self.__need_sort = False

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
		return sorted([a.pkg_solv for a in self.actions if a.needs_download])

	def download(self, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		# Get all download actions as a list.
		downloads = [d for d in self.downloads]

		# If there are no downloads, we can just stop here.
		if not downloads:
			return

		# Calculate downloadsize.
		download_size = sum([d.size for d in downloads])

		# Get free space of the download location.
		path = os.path.realpath(REPO_CACHE_DIR)
		while not os.path.ismount(path):
			path = os.path.dirname(path)
		path_stat = os.statvfs(path)

		if download_size >= path_stat.f_bavail * path_stat.f_bsize:
			raise DownloadError, _("Not enough space to download %s of packages.") \
				% util.format_size(download_size)

		logger.info(_("Downloading packages:"))
		time_start = time.time()

		i = 0
		for pkg in downloads:
			i += 1

			# Download the package file.
			bin_pkg = pkg.download(text="(%d/%d): " % (i, len(downloads)), logger=logger)

			# Search in every action if we need to replace the package.
			for action in self.actions:
				if not action.pkg_solv.uuid == bin_pkg.uuid:
					continue

				# Replace the package.
				action.pkg = bin_pkg

		# Write an empty line to the console when there have been any downloads.
		width, height = util.terminal_size()

		# Print a nice line.
		logger.info("-" * width)

		# Format and calculate download information.
		time_stop = time.time()
		download_time = time_stop - time_start
		download_speed = download_size / download_time
		download_speed = util.format_speed(download_speed)
		download_size = util.format_size(download_size)
		download_time = util.format_time(download_time)

		line = "%s | %5sB     %s     " % \
			(download_speed, download_size, download_time)
		line = " " * (width - len(line)) + line
		logger.info(line)
		logger.info("")

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
		if logger is None:
			logger = logging.getLogger("pakfire")

		if not self.actions:
			logger.info(_("Nothing to do"))
			return

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
		download_size = sum([d.size for d in self.downloads])
		if download_size:
			s.append(_("Total download size: %s") % util.format_size(download_size))

		# Show the size that is consumed by the new packages.
		if self.installsizechange > 0:
			s.append(_("Installed size: %s") % util.format_size(self.installsizechange))
		elif self.installsizechange < 0:
			freed_size = abs(self.installsizechange)
			s.append(_("Freed size: %s") % util.format_size(freed_size))
		s.append("")

		for line in s:
			logger.info(line)

	def cli_yesno(self):
		# Empty transactions are always denied.
		if not self.actions:
			return False

		return util.ask_user(_("Is this okay?"))

	def check(self, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")

		logger.info(_("Running Transaction Test"))

		# Initialize the check object.
		check = TransactionCheck(self.pakfire, self)

		for action in self.actions:
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

		# Search for actions we need to process.
		actions = []
		for action in self.actions:
			# Skip scripts.
			if isinstance(action, ActionScript):
				continue

			actions.append(action)

		# Make a nice progressbar.
		p = util.make_progress(_("Verifying signatures..."), len(actions))

		# Collect all errors.
		errors = []

		try:
			# Do the verification for every action.
			i = 0
			for action in actions:
				# Update the progressbar.
				if p:
					i += 1
					p.update(i)

				try:
					action.verify()

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

	def run(self, logger=None, signatures_mode=None):
		assert self.actions, "Cannot run an empty transaction."
		assert not self.__need_sort, "Did you forget to sort the transaction?"

		if logger is None:
			logger = logging.getLogger("pakfire")

		# Download all packages.
		# (don't add logger here because I do not want to see downloads
		# in the build logs on the build service)
		self.download()

		# Verify signatures.
		self.verify_signatures(mode=signatures_mode, logger=logger)

		# Run the transaction test
		self.check(logger=logger)

		logger.info(_("Running transaction"))
		# Run all actions in order and catch all kinds of ActionError.
		for action in self.actions:
			try:
				action.run()
			except ActionError, e:
				logger.error("Action finished with an error: %s - %s" % (action, e))

		logger.info("")

		# Commit repository metadata.
		self.local.commit()

		# Call sync to make sure all buffers are written to disk.
		sync()
