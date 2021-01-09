#!/usr/bin/python3
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

import argparse
import datetime
import logging
import os
import shutil
import signal
import sys
import tempfile
import time

from . import arch
from . import base
from . import builder
from . import client
from . import config
from . import daemon
from . import downloaders
from . import packages
from . import repository
from . import ui
from . import util

from .system import system
from .constants import *
from .i18n import _

class Cli(object):
	def __init__(self):
		self.ui = ui.cli.CliUI()

	def parse_cli(self):
		parser = argparse.ArgumentParser(
			description = _("Pakfire command line interface"),
		)
		subparsers = parser.add_subparsers()

		# Add common arguments
		self._add_common_arguments(parser)

		parser.add_argument("--root", metavar="PATH", default="/",
			help=_("The path where pakfire should operate in"))

		# check
		check = subparsers.add_parser("check", help=_("Check the system for any errors"))
		check.set_defaults(func=self.handle_check)

		# check-update
		check_update = subparsers.add_parser("check-update",
			help=_("Check, if there are any updates available"))
		check_update.set_defaults(func=self.handle_check_update)
		check_update.add_argument("--exclude", "-x", nargs="+",
			help=_("Exclude package from update"))
		check_update.add_argument("--allow-archchange", action="store_true",
			help=_("Allow changing the architecture of packages"))
		check_update.add_argument("--allow-downgrade", action="store_true",
			help=_("Allow downgrading of packages"))
		check_update.add_argument("--allow-vendorchange", action="store_true",
			help=_("Allow changing the vendor of packages"))

		# clean
		clean = subparsers.add_parser("clean", help=_("Cleanup all temporary files"))
		clean.set_defaults(func=self.handle_clean)

		# downgrade
		downgrade = subparsers.add_parser("downgrade", help=_("Downgrade one or more packages"))
		downgrade.add_argument("package", nargs="*",
			help=_("Give a name of a package to downgrade"))
		downgrade.add_argument("--allow-vendorchange", action="store_true",
			help=_("Allow changing the vendor of packages"))
		downgrade.add_argument("--disallow-archchange", action="store_true",
			help=_("Disallow changing the architecture of packages"))
		downgrade.set_defaults(func=self.handle_downgrade)

		# extract
		extract = subparsers.add_parser("extract",
			help=_("Extract a package to a directory"))
		extract.add_argument("package", nargs="+",
			help=_("Give name of the file to extract"))
		extract.add_argument("--target", nargs="?",
			help=_("Target directory where to extract to"))
		extract.set_defaults(func=self.handle_extract)

		# info
		info = subparsers.add_parser("info",
			help=_("Print some information about the given package(s)"))
		info.add_argument("package", nargs="+",
			help=_("Give at least the name of one package"))
		info.set_defaults(func=self.handle_info)

		# install
		install = subparsers.add_parser("install",
			help=_("Install one or more packages to the system"))
		install.add_argument("package", nargs="+",
			help=_("Give name of at least one package to install"))
		install.add_argument("--without-recommends", action="store_true",
			help=_("Don't install recommended packages"))
		install.set_defaults(func=self.handle_install)

		# provides
		provides = subparsers.add_parser("provides",
			help=_("Get a list of packages that provide a given file or feature"))
		provides.add_argument("pattern", nargs="+", help=_("File or feature to search for"))
		provides.set_defaults(func=self.handle_provides)

		# reinstall
		reinstall = subparsers.add_parser("reinstall",
			help=_("Reinstall one or more packages"))
		reinstall.add_argument("package", nargs="+",
			help=_("Give name of at least one package to reinstall"))
		reinstall.set_defaults(func=self.handle_reinstall)

		# remove
		remove = subparsers.add_parser("remove",
			help=_("Remove one or more packages from the system"))
		remove.add_argument("package", nargs="+",
			help=_("Give name of at least one package to remove"))
		remove.set_defaults(func=self.handle_remove)

		# repolist
		repolist = subparsers.add_parser("repolist",
			help=_("List all currently enabled repositories"))
		repolist.set_defaults(func=self.handle_repolist)

		# search
		search = subparsers.add_parser("search", help=_("Search for a given pattern"))
		search.add_argument("pattern", help=_("A pattern to search for"))
		search.set_defaults(func=self.handle_search)

		# sync
		sync = subparsers.add_parser("sync",
			help=_("Sync all installed with the latest one in the distribution"))
		sync.set_defaults(func=self.handle_sync)

		# update
		update = subparsers.add_parser("update",
			help=_("Update the whole system or one specific package"))
		update.add_argument("package", nargs="*",
			help=_("Give a name of a package to update or leave emtpy for all"))
		update.add_argument("--exclude", "-x", nargs="+",
			help=_("Exclude package from update"))
		update.add_argument("--allow-archchange", action="store_true",
			help=_("Allow changing the architecture of packages"))
		update.add_argument("--allow-downgrade", action="store_true",
			help=_("Allow downgrading of packages"))
		update.add_argument("--allow-vendorchange", action="store_true",
			help=_("Allow changing the vendor of packages"))
		update.set_defaults(func=self.handle_update)

		return parser.parse_args()

	def _add_common_arguments(self, parser, offline_switch=True):
		parser.add_argument("--version", action="version",
			version="%(prog)s " + PAKFIRE_VERSION)

		parser.add_argument("-v", "--verbose", action="store_true",
			help=_("Enable verbose output."))

		parser.add_argument("-c", "--config", nargs="?",
			help=_("Path to a configuration file to load."))

		parser.add_argument("--disable-repo", nargs="*", metavar="REPO",
			help=_("Disable a repository temporarily."), default=[])

		parser.add_argument("--enable-repo", nargs="*", metavar="REPO",
			help=_("Enable a repository temporarily."), default=[])

		if offline_switch:
			parser.add_argument("--offline", action="store_true",
				help=_("Run pakfire in offline mode."))

	def pakfire(self, ns):
		p = base.Pakfire(path=ns.root, offline=ns.offline)

		# Disable repositories.
		for repo_name in ns.disable_repo:
			repo = p.get_repo(repo_name)
			repo.enabled = False

		# Enable repositories.
		for repo_name in ns.enable_repo:
			repo = p.get_repo(repo_name)
			repo.enabled = True

		return p

	def run(self):
		args = self.parse_cli()
		assert args.func, "Argument function not defined"

		try:
			return args.func(args)

		except KeyboardInterrupt:
			self.ui.message(_("Received keyboard interupt (Ctrl-C). Exiting."),
				level=logging.CRITICAL)

			return 128 + signal.SIGINT

		except DependencyError as e:
			self.ui.message(_("One or more dependencies could not been resolved"))
			self.ui.message("") # empty line

			# This exception provides a list of all problems
			problems, = e.args

			# List all problems
			for problem in problems:
				self.ui.message("  * %s" % problem)

				self.ui.message("    %s" % _("Possible solutions are:"))
				for solution in problem.solutions:
					self.ui.message("    * %s" % solution)

				# Add another empty line
				self.ui.message("")

			return 4

		# Catch all errors and show a user-friendly error message.
		except Error as e:
			self.ui.message(_("An error has occured when running Pakfire"), level=logging.CRITICAL)

			self.ui.message(_("%s: %s") % (e.__class__.__name__, e.message),
				level=logging.ERROR)

			return e.exit_code

	def _dump_transaction(self, transaction):
		"""
			Dumps the transaction
		"""
		t = transaction.dump()

		for line in t.splitlines():
			self.ui.message(line)

	def _download_transaction(self, transaction):
		"""
			Downloads all packages required for this transaction
		"""
		d = downloaders.TransactionDownloader(self.pakfire, transaction)

		# Run the download
		d.download()

	def _execute_transaction(self, transaction):
		# Don't do anything if the transaction is empty
		if len(transaction) == 0:
			self.ui.message(_("Nothing to do"))
			return

		# Dump the transaction
		self._dump_transaction(transaction)

		# Ask the user to confirm to go ahead
		if not self.ui.confirm():
			self.ui.message(_("Aborted by user"))
			return

		# Download transaction
		self._download_transaction(transaction)

		# Run the transaction
		transaction.run()

	def handle_info(self, ns):
		with self.pakfire(ns) as p:
			for pkg in p.info(ns.package):
				s = pkg.dump(long=ns.verbose)
				self.ui.message(s)

	def handle_search(self, ns):
		with self.pakfire(ns) as p:
			for pkg in p.search(ns.pattern):
				# Skip any -debuginfo packages
				if pkg.name.endswith("-debuginfo"):
					continue

				self.ui.message("%-24s: %s" % (pkg.name, pkg.summary))

	def handle_update(self, ns, check=False):
		with self.pakfire(ns) as p:
			transaction = p.update(
				ns.package, excludes=ns.exclude,
				allow_archchange=ns.allow_archchange,
				allow_vendorchange=ns.allow_vendorchange,
			)

			# If we are only checking for updates,
			# we dump the transaction and exit here.
			if check:
				self._dump_transaction(transaction)
				return

			# Otherwise we execute the transaction
			self._execute_transaction(transaction)

	def handle_sync(self, ns):
		with self.pakfire(ns) as p:
			transaction = p.update(
				allow_archchange=True,
				allow_vendorchange=True,
			)

			self._execute_transaction(transaction)

	def handle_check_update(self, ns):
		self.handle_update(ns, check=True)

	def handle_downgrade(self, ns, **args):
		with self.pakfire(ns) as p:
			p.downgrade(
				self.args.package,
				allow_vendorchange=self.args.allow_vendorchange,
				allow_archchange=not self.args.disallow_archchange,
				**args
			)

	def handle_install(self, ns):
		with self.pakfire(ns) as p:
			transaction = p.install(ns.package, without_recommends=ns.without_recommends)

			# Execute the transaction
			self._execute_transaction(transaction)

	def handle_reinstall(self, ns):
		with self.pakfire(ns) as p:
			transaction = p.reinstall(ns.package)

			# Execute the transaction
			self._execute_transaction(transaction)

	def handle_remove(self, ns):
		with self.pakfire(ns) as p:
			transaction = p.erase(ns.package)

			self._execute_transaction(transaction)

	def handle_provides(self, ns, long=False):
		with self.pakfire(ns) as p:
			for pkg in p.provides(ns.pattern):
				s = pkg.dump(long=long)
				print(s)

	def handle_repolist(self, ns):
		with self.pakfire(ns) as p:
			FORMAT = " %-20s %8s %12s %12s "
			title = FORMAT % (_("Repository"), _("Enabled"), _("Priority"), _("Packages"))
			print(title)
			print("=" * len(title)) # spacing line

			for repo in p.repos:
				print(FORMAT % (repo.name, repo.enabled, repo.priority, len(repo)))

	def handle_clean(self, ns):
		self.ui.message(_("Cleaning up everything..."))

		p = self.pakfire(ns)
		p.clean()

	def handle_check(self, ns):
		with self.pakfire(ns) as p:
			# This will throw an exception when there are errors
			transaction = p.check()

			self.ui.message(_("Everything okay"))

	def handle_extract(self, ns):
		with self.pakfire(ns) as p:
			p.extract(ns.package, target=ns.target)


class CliBuilder(Cli):
	def __init__(self):
		Cli.__init__(self)

		# Check if we are already running in a pakfire container. In that
		# case, we cannot start another pakfire-builder.
		if os.environ.get("container", None) == "pakfire-builder":
			raise PakfireContainerError(_("You cannot run pakfire-builder in a pakfire chroot"))

	def parse_cli(self):
		parser = argparse.ArgumentParser(
			description = _("Pakfire builder command line interface"),
		)
		subparsers = parser.add_subparsers()

		# Add common arguments
		self._add_common_arguments(parser)

		# Add additional arguments
		parser.add_argument("--arch", "-a", nargs="?",
			help=_("Run pakfire for the given architecture"))
		parser.add_argument("--distro", nargs="?",
			help=_("Choose the distribution configuration to use for build"))

		# build
		build = subparsers.add_parser("build", help=_("Build one or more packages"))
		build.add_argument("package", nargs=1,
			help=_("Give name of at least one package to build"))
		build.set_defaults(func=self.handle_build)

		build.add_argument("--resultdir", nargs="?",
			help=_("Path were the output files should be copied to"))
		build.add_argument("-m", "--mode", nargs="?", default="development",
			help=_("Mode to run in. Is either 'release' or 'development' (default)"))
		build.add_argument("--after-shell", action="store_true",
			help=_("Run a shell after a successful build"))
		build.add_argument("--skip-install-test", action="store_true",
			help=_("Do not perform the install test"))
		build.add_argument("--private-network", action="store_true",
			help=_("Disable network in container"))

		# clean
		clean = subparsers.add_parser("clean", help=_("Cleanup all temporary files"))
		clean.set_defaults(func=self.handle_clean)

		# dist
		dist = subparsers.add_parser("dist", help=_("Generate a source package"))
		dist.add_argument("package", nargs="+", help=_("Give name(s) of a package(s)"))
		dist.set_defaults(func=self.handle_dist)

		dist.add_argument("--resultdir", nargs="?",
			help=_("Path were the output files should be copied to"))

		# extract
		extract = subparsers.add_parser("extract", help=_("Extract a package to a directory"))
		extract.add_argument("package", nargs="+",
			help=_("Give name of the file to extract"))
		extract.add_argument("--target", nargs="?",
			help=_("Target directory where to extract to"))
		extract.set_defaults(func=self.handle_extract)

		# info
		info = subparsers.add_parser("info",
			help=_("Print some information about the given package(s)"))
		info.add_argument("package", nargs="+",
			help=_("Give at least the name of one package."))
		info.set_defaults(func=self.handle_info, verbose=True)

		# provides
		provides = subparsers.add_parser("provides",
			help=_("Get a list of packages that provide a given file or feature"))
		provides.add_argument("pattern", nargs="+",
			help=_("File or feature to search for"))
		provides.set_defaults(func=self.handle_provides)

		# repolist
		repolist = subparsers.add_parser("repolist",
			help=_("List all currently enabled repositories"))
		repolist.set_defaults(func=self.handle_repolist)

		# search
		search = subparsers.add_parser("search", help=_("Search for a given pattern"))
		search.add_argument("pattern", help=_("A pattern to search for"))
		search.set_defaults(func=self.handle_search)

		# shell
		shell = subparsers.add_parser("shell", help=_("Go into a build shell"))
		shell.add_argument("package", nargs="?", help=_("Give name of a package"))
		shell.set_defaults(func=self.handle_shell)

		shell.add_argument("-m", "--mode", nargs="?", default="development",
			help=_("Mode to run in. Is either 'release' or 'development' (default)."))
		shell.add_argument("--private-network", action="store_true",
			help=_("Disable network in container"))

		# update
		update = subparsers.add_parser("update", help=_("Update the package indexes"))
		update.set_defaults(func=self.handle_update)

		return parser.parse_args()

	def builder(self, ns):
		a = arch.Arch(ns.arch or system.native_arch)

		b = builder.Builder(arch=a)

		return b

	def handle_build(self, ns):
		package, = ns.package

		# Initialise a builder instance and build this package
		with self.builder(ns) as b:
			b.build(package)

	def handle_shell(self, ns):
		with self.builder(ns) as b:
			b.shell()

	def handle_dist(self, ns):
		# Get the packages from the command line options
		pkgs = []

		for pkg in ns.package:
			# Check, if we got a regular file
			if os.path.exists(pkg):
				pkg = os.path.abspath(pkg)
				pkgs.append(pkg)

			else:
				raise FileNotFoundError(pkg)

		# Put packages to where the user said or our
		# current working directory.
		resultdir = ns.resultdir or os.getcwd()

		p = self.pakfire(ns)
		for pkg in pkgs:
			p.dist(pkg, resultdir=resultdir)

	def handle_provides(self):
		Cli.handle_provides(self, int=True)


class CliBuilderIntern(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire builder command line interface."),
		)
		self._add_common_arguments(self.parser)

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_build()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.action2func = {
			"build"       : self.handle_build,
		}

	def parse_command_build(self):
		# Implement the "build" command.
		sub_build = self.sub_commands.add_parser("build",
			help=_("Build one or more packages."))
		sub_build.add_argument("package", nargs=1,
			help=_("Give name of at least one package to build."))
		sub_build.add_argument("action", action="store_const", const="build")

		sub_build.add_argument("-a", "--arch",
			help=_("Build the package for the given architecture."))
		sub_build.add_argument("--resultdir", nargs="?",
			help=_("Path were the output files should be copied to."))
		sub_build.add_argument("-m", "--mode", nargs="?", default="development",
			help=_("Mode to run in. Is either 'release' or 'development' (default)."))
		sub_build.add_argument("--nodeps", action="store_true",
			help=_("Do not verify build dependencies."))
		sub_build.add_argument("--prepare", action="store_true",
			help=_("Only run the prepare stage."))

	def handle_build(self):
		# Get the package descriptor from the command line options
		pkg = self.args.package[0]

		# Check, if we got a regular file
		if os.path.exists(pkg):
			pkg = os.path.abspath(pkg)
		else:
			raise FileNotFoundError(pkg)

		# Create pakfire instance.
		c = config.ConfigBuilder()
		p = base.Pakfire(arch = self.args.arch, config = c)

		# Disable all repositories.
		if self.args.nodeps:
			p.repos.disable_repo("*")

		# Limit stages that are to be run.
		if self.args.prepare:
			stages = ["prepare"]
		else:
			stages = None

		p.build(pkg, resultdir=self.args.resultdir, stages=stages)


class CliClient(Cli):
	def __init__(self):
		# Create connection to pakfire hub
		self.client = client.Client()

	def parse_cli(self):
		parser = argparse.ArgumentParser(
			description = _("Pakfire client command line interface"),
		)
		subparsers = parser.add_subparsers(help=_("sub-command help"))

		# Add common arguments
		self._add_common_arguments(parser, offline_switch=False)

		# build
		build = subparsers.add_parser("build", help=_("Build a package remote"))
		build.add_argument("packages", nargs="+", help=_("Package(s) to build"))
		build.set_defaults(func=self.handle_build)

		build.add_argument("-a", "--arch",
			help=_("Build the package(s) for the given architecture only"))

		# check-connection
		check_connection = subparsers.add_parser("check-connection",
			help=_("Check the connection to the hub"))
		check_connection.set_defaults(func=self.handle_check_connection)

		# upload
		upload = subparsers.add_parser("upload", help=_("Upload a file to the build service"))
		upload.add_argument("file", nargs=1, help=_("Filename"))
		upload.set_defaults(func=self.handle_upload)

		# watch-build
		watch_build = subparsers.add_parser("watch-build", help=_("Watch the status of a build"))
		watch_build.add_argument("id", nargs=1, help=_("Build ID"))
		watch_build.set_defaults(func=self.handle_watch_build)

		# watch-job
		watch_job = subparsers.add_parser("watch-job", help=_("Watch the status of a job"))
		watch_job.add_argument("id", nargs=1, help=_("Job ID"))
		watch_job.set_defaults(func=self.handle_watch_job)

		return parser.parse_args()

	def handle_build(self, ns):
		# Create a temporary directory.
		temp_dir = tempfile.mkdtemp()

		# Format arches.
		if ns.arch:
			arches = self.args.arch.split(",")
		else:
			arches = None

		try:
			# Package all packages first and save the actual filenames
			packages = []

			for package in ns.packages:
				if package.endswith(".%s" % MAKEFILE_EXTENSION):
					# Create a source package from the makefile.
					p = self.pakfire()
					package = p.dist(package, temp_dir)
					packages.append(package)

				elif package.endswith(".%s" % PACKAGE_EXTENSION):
					packages.append(package)

				else:
					raise Exception("Unknown filetype: %s" % package)

			assert packages

			# Upload the packages to the build service
			for package in packages:
				build = self.client.create_build(package, type="scratch", arches=arches)

				# Show information about the uploaded build
				summary = build.dump()
				for line in summary.splitlines():
					print("  %s" % line)

		finally:
			# Cleanup the temporary directory and all files.
			if os.path.exists(temp_dir):
				shutil.rmtree(temp_dir, ignore_errors=True)

	def handle_check_connection(self, ns):
		success = self.client.check_connection()

		if success:
			print("%s: %s" % (_("Connection OK"), success))

	def handle_upload(self, ns):
		for path in ns.file:
			self.client.upload_file(path)

	def handle_watch_build(self, ns):
		build = self.client.get_build(ns.id[0])

		return self._watch_something(build)

	def handle_watch_job(self, ns):
		job = self.client.get_job(ns.id[0])

		return self._watch_something(job)

	def _watch_something(self, o):
		while True:
			s = o.dump()
			print(s)

			# Break the loop if the build/job is not active any more
			# (since we don't expect any changes)
			if not o.is_active():
				break

			time.sleep(60)

			# Update data before the next loop is shown
			o.refresh()


class CliDaemon(Cli):
	def parse_cli(self):
		parser = argparse.ArgumentParser(
			description = _("Pakfire daemon command line interface"),
		)
		self._add_common_arguments(parser, offline_switch=False)

		# There is only one default action
		parser.set_defaults(func=self.handle_run)

		return parser.parse_args()

	def handle_run(self, ns):
		"""
			Runs the pakfire daemon
		"""
		d = daemon.PakfireDaemon()

		try:
			d.run()

		# We cannot just kill the daemon, it needs a smooth shutdown
		except (SystemExit, KeyboardInterrupt):
			d.shutdown()


class CliKey(Cli):
	def parse_cli(self):
		parser = argparse.ArgumentParser(
			description = _("Pakfire key command line interface"),
		)
		subparsers = parser.add_subparsers()

		# Add common arguments
		self._add_common_arguments(parser)

		# delete
		delete = subparsers.add_parser("delete", help=_("Delete a key from the local keyring"))
		delete.add_argument("fingerprint", nargs="+", help=_("The fingerprint of the key to delete"))
		delete.set_defaults(func=self.handle_delete)

		# export
		export = subparsers.add_parser("export", help=_("Export a key to a file"))
		export.add_argument("fingerprint", nargs=1,
			help=_("The fingerprint of the key to export"))
		export.add_argument("--filename", nargs="*", help=_("Write the key to this file"))
		export.add_argument("--secret", action="store_true",
			help=_("Export the secret key"))
		export.set_defaults(func=self.handle_export)

		# import
		_import = subparsers.add_parser("import", help=_("Import a key from file"))
		_import.add_argument("filename", nargs="+", help=_("Filename of that key to import"))
		_import.set_defaults(func=self.handle_import)

		# generate
		generate = subparsers.add_parser("generate", help=_("Import a key from file"))
		generate.add_argument("--realname", nargs=1,
			help=_("The real name of the owner of this key"))
		generate.add_argument("--email", nargs=1,
			help=_("The email address of the owner of this key"))
		generate.set_defaults(func=self.handle_generate)

		# list
		list = subparsers.add_parser("list", help=_("List all imported keys"))
		list.set_defaults(func=self.handle_list)

		return parser.parse_args()

	def parse_command_sign(self):
		# Implement the "sign" command.
		sub_sign = self.sub_commands.add_parser("sign",
			help=_("Sign one or more packages."))
		sub_sign.add_argument("--key", "-k", nargs=1,
			help=_("Key that is used sign the package(s)."))
		sub_sign.add_argument("package", nargs="+",
			help=_("Package(s) to sign."))
		sub_sign.add_argument("action", action="store_const", const="sign")

	def parse_command_verify(self):
		# Implement the "verify" command.
		sub_verify = self.sub_commands.add_parser("verify",
			help=_("Verify one or more packages."))
		#sub_verify.add_argument("--key", "-k", nargs=1,
		#	help=_("Key that is used verify the package(s)."))
		sub_verify.add_argument("package", nargs="+",
			help=_("Package(s) to verify."))
		sub_verify.add_argument("action", action="store_const", const="verify")

	def handle_generate(self, ns):
		p = self.pakfire(ns)

		print(_("Generating the key may take a moment..."))
		print()

		key = p.generate_key("%s <%s>" % (ns.realname.pop(), ns.email.pop()))

	def handle_list(self, ns):
		p = self.pakfire(ns)

		for key in p.keys:
			print(key)

	def handle_export(self, ns):
		p = self.pakfire(ns)

		for fingerprint in ns.fingerprint:
			key = p.get_key(fingerprint)
			if not key:
				print(_("Could not find key with fingerprint %s") % fingerprint)
				continue

			data = key.export(ns.secret)

			for file in ns.filename:
				with open(file, "w") as f:
					f.write(data)
			else:
				print(data)

	def handle_import(self, ns):
		p = self.pakfire(ns)

		for filename in ns.filename:
			with open(filename) as f:
				data = f.read()

				keys = p.import_key(data)
				for key in keys:
					print(key)

	def handle_delete(self, ns):
		p = self.pakfire(ns)

		for fingerprint in ns.fingerprint:
			key = p.get_key(fingerprint)
			if key:
				key.delete()

	def handle_sign(self):
		# Get the files from the command line options
		files = []

		for file in self.args.package:
			# Check, if we got a regular file
			if os.path.exists(file):
				file = os.path.abspath(file)
				files.append(file)

			else:
				raise FileNotFoundError(file)

		key = self.args.key[0]

		# Create pakfire instance.
		p = self.create_pakfire()

		for file in files:
			# Open the package.
			pkg = packages.open(p, None, file)

			print(_("Signing %s...") % pkg.friendly_name)
			pkg.sign(key)

	def handle_verify(self):
		# TODO needs to use new key code from libpakfire

		# Get the files from the command line options
		files = []

		for file in self.args.package:
			# Check, if we got a regular file
			if os.path.exists(file) and not os.path.isdir(file):
				file = os.path.abspath(file)
				files.append(file)

		# Create pakfire instance.
		p = self.create_pakfire()

		for file in files:
			# Open the package.
			pkg = packages.open(p, None, file)

			print(_("Verifying %s...") % pkg.friendly_name)
			sigs = pkg.verify()

			for sig in sigs:
				key = p.keyring.get_key(sig.fpr)
				if key:
					subkey = key.subkeys[0]

					print("  %s %s" % (subkey.fpr[-16:], key.uids[0].uid))
					if sig.validity:
						print("    %s" % _("This signature is valid."))

				else:
					print("  %s <%s>" % (sig.fpr, _("Unknown key")))
					print("    %s" % _("Could not check if this signature is valid."))

				created = datetime.datetime.fromtimestamp(sig.timestamp)
				print("    %s" % _("Created: %s") % created)

				if sig.exp_timestamp:
					expires = datetime.datetime.fromtimestamp(sig.exp_timestamp)
					print("    %s" % _("Expires: %s") % expires)

			print() # Empty line
