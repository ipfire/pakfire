#!/usr/bin/python

import logging
import os
import progressbar
import sys
import time

import packages
import satsolver
import util

from constants import *
from i18n import _

PKG_DUMP_FORMAT = " %-21s %-8s %-21s %-18s %6s "

# Import all actions directly.
from actions import *

class Transaction(object):
	action_classes = {
		"install"   : [ActionScriptPreIn, ActionInstall, ActionScriptPostIn, ActionScriptPostTransIn],
		"reinstall" : [ActionScriptPreIn, ActionInstall, ActionScriptPostIn, ActionScriptPostTransIn],
		"erase"     : [ActionScriptPreUn, ActionRemove, ActionScriptPostUn, ActionScriptPostTransUn],
		"update"    : [ActionScriptPreUp, ActionUpdate,  ActionScriptPostUp, ActionScriptPostTransUp],
		"cleanup"   : [ActionCleanup,],
		"downgrade" : [ActionScriptPreUp, ActionDowngrade, ActionScriptPostUp, ActionScriptPostTransUp],
		"change"    : [ActionChange,],
	}

	def __init__(self, pakfire):
		self.pakfire = pakfire
		self.actions = []

		self.installsizechange = 0

	@classmethod
	def from_solver(cls, pakfire, solver, _transaction):
		# Create a new instance of our own transaction class.
		transaction = cls(pakfire)

		# Save installsizechange.
		transaction.installsizechange = _transaction.get_installsizechange()

		# Get all steps that need to be done from the solver.
		steps = _transaction.steps()
		if not steps:
			return

		actions = []
		actions_post = []

		for step in steps:
			action_name = step.get_type()
			pkg = packages.SolvPackage(pakfire, step.get_solvable())

			try:
				classes = transaction.action_classes[action_name]
			except KeyError:
				raise Exception, "Unknown action required: %s" % action_name

			for action_cls in classes:
				action = action_cls(pakfire, pkg)
				assert isinstance(action, Action), action

				if isinstance(action, ActionScriptPostTrans):
					actions_post.append(action)
				else:
					actions.append(action)

		transaction.actions += actions + actions_post

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
		# Get all download actions as a list.
		downloads = [d for d in self.downloads]
		downloads.sort()

		# If there are no downloads, we can just stop here.
		if not downloads:
			return

		logging.info(_("Downloading packages:"))
		time_start = time.time()

		# Calculate downloadsize.
		download_size = 0
		for action in downloads:
			download_size += action.pkg.size

		i = 0
		for action in downloads:
			i += 1
			action.download(text="(%d/%d): " % (i, len(downloads)))

		# Write an empty line to the console when there have been any downloads.
		width, height = util.terminal_size()

		# Print a nice line.
		logging.info("-" * width)

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
		logging.info(line)
		logging.info("")

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

		# Show the size that is consumed by the new packages.
		if self.installsizechange > 0:
			s.append(_("Installed size: %s") % util.format_size(self.installsizechange))
		elif self.installsizechange < 0:
			s.append(_("Freed size: %s") % util.format_size(self.installsizechange))
		s.append("")

		for line in s:
			logger.info(line)

	def cli_yesno(self, logger=None):
		self.dump(logger)

		return util.ask_user(_("Is this okay?"))

	def run(self):
		# Download all packages.
		self.download()

		logging.info(_("Running transaction"))
		# Run all actions in order and catch all kinds of ActionError.
		for action in self.actions:
			try:
				action.run()
			except ActionError, e:
				logging.error("Action finished with an error: %s - %s" % (action, e))

		logging.info("")
