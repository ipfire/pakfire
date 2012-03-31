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

import argparse
import datetime
import os
import shutil
import sys
import tempfile

import pakfire.api as pakfire

import client
import config
import logger
import packages
import repository
import server
import util

from system import system
from constants import *
from i18n import _

# Initialize a very simple logging that is removed when a Pakfire instance
# is started.
logger.setup_logging()

class Cli(object):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire command line interface."),
		)

		self.parse_common_arguments()

		self.parser.add_argument("--root", metavar="PATH",
			default="/",
			help=_("The path where pakfire should operate in."))

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_install()
		self.parse_command_reinstall()
		self.parse_command_remove()
		self.parse_command_info()
		self.parse_command_search()
		self.parse_command_check_update()
		self.parse_command_update()
		self.parse_command_downgrade()
		self.parse_command_provides()
		self.parse_command_grouplist()
		self.parse_command_groupinstall()
		self.parse_command_repolist()
		self.parse_command_clean()
		self.parse_command_check()
		self.parse_command_resolvdep()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.action2func = {
			"install"      : self.handle_install,
			"reinstall"    : self.handle_reinstall,
			"remove"       : self.handle_remove,
			"check_update" : self.handle_check_update,
			"update"       : self.handle_update,
			"downgrade"    : self.handle_downgrade,
			"info"         : self.handle_info,
			"search"       : self.handle_search,
			"provides"     : self.handle_provides,
			"grouplist"    : self.handle_grouplist,
			"groupinstall" : self.handle_groupinstall,
			"repolist"     : self.handle_repolist,
			"clean_all"    : self.handle_clean_all,
			"check"        : self.handle_check,
			"resolvdep"    : self.handle_resolvdep,
		}

	@property
	def pakfire_args(self):
		ret = { "mode" : "normal" }

		if hasattr(self.args, "root"):
			ret["path"] = self.args.root

		if hasattr(self.args, "disable_repo"):
			ret["disable_repos"] = self.args.disable_repo

		if hasattr(self.args, "enable_repo"):
			ret["enable_repos"] = self.args.enable_repo

		if hasattr(self.args, "offline"):
			ret["offline"] = self.args.offline

		if hasattr(self.args, "config"):
			ret["configs"] = self.args.config
		else:
			ret["configs"] = None

		return ret

	def parse_common_arguments(self, repo_manage_switches=True, offline_switch=True):
		self.parser.add_argument("--version", action="version",
			version="%(prog)s " + PAKFIRE_VERSION)

		self.parser.add_argument("-v", "--verbose", action="store_true",
			help=_("Enable verbose output."))

		self.parser.add_argument("-c", "--config", nargs="?",
			help=_("Path to a configuration file to load."))

		if repo_manage_switches:
			self.parser.add_argument("--disable-repo", nargs="*", metavar="REPO",
				help=_("Disable a repository temporarily."))

			self.parser.add_argument("--enabled-repo", nargs="*", metavar="REPO",
				help=_("Enable a repository temporarily."))

		if offline_switch:
			self.parser.add_argument("--offline", action="store_true",
				help=_("Run pakfire in offline mode."))

	def parse_command_install(self):
		# Implement the "install" command.
		sub_install = self.sub_commands.add_parser("install",
			help=_("Install one or more packages to the system."))
		sub_install.add_argument("package", nargs="+",
			help=_("Give name of at least one package to install."))
		sub_install.add_argument("action", action="store_const", const="install")

	def parse_command_reinstall(self):
		# Implement the "reinstall" command.
		sub_install = self.sub_commands.add_parser("reinstall",
			help=_("Reinstall one or more packages."))
		sub_install.add_argument("package", nargs="+",
			help=_("Give name of at least one package to reinstall."))
		sub_install.add_argument("action", action="store_const", const="reinstall")

	def parse_command_remove(self):
		# Implement the "remove" command.
		sub_remove = self.sub_commands.add_parser("remove",
			help=_("Remove one or more packages from the system."))
		sub_remove.add_argument("package", nargs="+",
			help=_("Give name of at least one package to remove."))
		sub_remove.add_argument("action", action="store_const", const="remove")

	@staticmethod
	def _parse_command_update(parser):
		parser.add_argument("package", nargs="*",
			help=_("Give a name of a package to update or leave emtpy for all."))
		parser.add_argument("--exclude", "-x", nargs="+",
			help=_("Exclude package from update."))
		parser.add_argument("--allow-vendorchange", action="store_true",
			help=_("Allow changing the vendor of packages."))
		parser.add_argument("--allow-archchange", action="store_true",
			help=_("Allow changing the architecture of packages."))

	def parse_command_update(self):
		# Implement the "update" command.
		sub_update = self.sub_commands.add_parser("update",
			help=_("Update the whole system or one specific package."))
		sub_update.add_argument("action", action="store_const", const="update")
		self._parse_command_update(sub_update)

	def parse_command_check_update(self):
		# Implement the "check-update" command.
		sub_check_update = self.sub_commands.add_parser("check-update",
			help=_("Check, if there are any updates available."))
		sub_check_update.add_argument("action", action="store_const", const="check_update")
		self._parse_command_update(sub_check_update)

	def parse_command_downgrade(self):
		# Implement the "downgrade" command.
		sub_downgrade = self.sub_commands.add_parser("downgrade",
			help=_("Downgrade one or more packages."))
		sub_downgrade.add_argument("package", nargs="*",
			help=_("Give a name of a package to downgrade."))
		sub_downgrade.add_argument("--allow-vendorchange", action="store_true",
			help=_("Allow changing the vendor of packages."))
		sub_downgrade.add_argument("--allow-archchange", action="store_true",
			help=_("Allow changing the architecture of packages."))
		sub_downgrade.add_argument("action", action="store_const", const="downgrade")

	def parse_command_info(self):
		# Implement the "info" command.
		sub_info = self.sub_commands.add_parser("info",
			help=_("Print some information about the given package(s)."))
		sub_info.add_argument("package", nargs="+",
			help=_("Give at least the name of one package."))
		sub_info.add_argument("action", action="store_const", const="info")

	def parse_command_search(self):
		# Implement the "search" command.
		sub_search = self.sub_commands.add_parser("search",
			help=_("Search for a given pattern."))
		sub_search.add_argument("pattern",
			help=_("A pattern to search for."))
		sub_search.add_argument("action", action="store_const", const="search")

	def parse_command_provides(self):
		# Implement the "provides" command
		sub_provides = self.sub_commands.add_parser("provides",
			help=_("Get a list of packages that provide a given file or feature."))
		sub_provides.add_argument("pattern", nargs="+",
			help=_("File or feature to search for."))
		sub_provides.add_argument("action", action="store_const", const="provides")

	def parse_command_grouplist(self):
		# Implement the "grouplist" command
		sub_grouplist = self.sub_commands.add_parser("grouplist",
			help=_("Get list of packages that belong to the given group."))
		sub_grouplist.add_argument("group", nargs=1,
			help=_("Group name to search for."))
		sub_grouplist.add_argument("action", action="store_const", const="grouplist")

	def parse_command_groupinstall(self):
		# Implement the "grouplist" command
		sub_groupinstall = self.sub_commands.add_parser("groupinstall",
			help=_("Install all packages that belong to the given group."))
		sub_groupinstall.add_argument("group", nargs=1,
			help=_("Group name."))
		sub_groupinstall.add_argument("action", action="store_const", const="groupinstall")

	def parse_command_repolist(self):
		# Implement the "repolist" command
		sub_repolist = self.sub_commands.add_parser("repolist",
			help=_("List all currently enabled repositories."))
		sub_repolist.add_argument("action", action="store_const", const="repolist")

	def parse_command_clean(self):
		sub_clean = self.sub_commands.add_parser("clean", help=_("Cleanup commands."))

		sub_clean_commands = sub_clean.add_subparsers()

		self.parse_command_clean_all(sub_clean_commands)

	def parse_command_clean_all(self, sub_commands):
		sub_create = sub_commands.add_parser("all",
			help=_("Cleanup all temporary files."))
		sub_create.add_argument("action", action="store_const", const="clean_all")

	def parse_command_check(self):
		# Implement the "check" command
		sub_check = self.sub_commands.add_parser("check",
			help=_("Check the system for any errors."))
		sub_check.add_argument("action", action="store_const", const="check")

	def parse_command_resolvdep(self):
		# Implement the "resolvdep" command.
		sub_resolvdep = self.sub_commands.add_parser("resolvdep",
			help=_("Check the dependencies for a particular package."))
		sub_resolvdep.add_argument("package", nargs=1,
			help=_("Give name of at least one package to check."))
		sub_resolvdep.add_argument("action", action="store_const", const="resolvdep")

	def run(self):
		action = self.args.action

		try:
			func = self.action2func[action]
		except KeyError:
			raise Exception, "Unhandled action: %s" % action

		return func()

	def handle_info(self, long=False):
		pkgs = pakfire.info(self.args.package, **self.pakfire_args)

		for pkg in pkgs:
			print pkg.dump(long=long)

	def handle_search(self):
		pkgs = pakfire.search(self.args.pattern, **self.pakfire_args)

		for pkg in pkgs:
			print pkg.dump(short=True)

	def handle_update(self, **args):
		args.update(self.pakfire_args)

		pakfire.update(self.args.package, excludes=self.args.exclude,
			allow_vendorchange=self.args.allow_vendorchange,
			allow_archchange=self.args.allow_archchange,
			**args)

	def handle_check_update(self):
		self.handle_update(check=True)

	def handle_downgrade(self, **args):
		args.update(self.pakfire_args)

		pakfire.downgrade(self.args.package,
			allow_vendorchange=self.args.allow_vendorchange,
			allow_archchange=self.args.allow_archchange,
			**args)

	def handle_install(self):
		pakfire.install(self.args.package, **self.pakfire_args)

	def handle_reinstall(self):
		pakfire.reinstall(self.args.package, **self.pakfire_args)

	def handle_remove(self):
		pakfire.remove(self.args.package, **self.pakfire_args)

	def handle_provides(self):
		pkgs = pakfire.provides(self.args.pattern, **self.pakfire_args)

		for pkg in pkgs:
			print pkg.dump()

	def handle_grouplist(self):
		pkgs = pakfire.grouplist(self.args.group[0], **self.pakfire_args)

		for pkg in pkgs:
			print " * %s" % pkg

	def handle_groupinstall(self):
		pakfire.groupinstall(self.args.group[0], **self.pakfire_args)

	def handle_repolist(self):
		repos = pakfire.repo_list(**self.pakfire_args)

		FORMAT = " %-20s %8s %12s %12s "

		title = FORMAT % (_("Repository"), _("Enabled"), _("Priority"), _("Packages"))
		print title
		print "=" * len(title) # spacing line

		for repo in repos:
			# Skip the installed repository.
			if repo.name == "installed":
				continue

			print FORMAT % (repo.name, repo.enabled, repo.priority, len(repo))

	def handle_clean_all(self):
		print _("Cleaning up everything...")

		pakfire.clean_all(**self.pakfire_args)

	def handle_check(self):
		pakfire.check(**self.pakfire_args)

	def handle_resolvdep(self):
		(pkg,) = self.args.package

		solver = pakfire.resolvdep(pkg, **self.pakfire_args)

		assert solver.status
		solver.transaction.dump()


class CliBuilder(Cli):
	def __init__(self):
		# Check if we are already running in a pakfire container. In that
		# case, we cannot start another pakfire-builder.
		if os.environ.get("container", None) == "pakfire-builder":
			raise PakfireContainerError, _("You cannot run pakfire-builder in a pakfire chroot.")

		self.parser = argparse.ArgumentParser(
			description = _("Pakfire builder command line interface."),
		)

		self.parse_common_arguments()

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_build()
		self.parse_command_dist()
		self.parse_command_info()
		self.parse_command_search()
		self.parse_command_shell()
		self.parse_command_update()
		self.parse_command_provides()
		self.parse_command_grouplist()
		self.parse_command_repolist()
		self.parse_command_clean()
		self.parse_command_resolvdep()
		self.parse_command_cache()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.action2func = {
			"build"       : self.handle_build,
			"dist"        : self.handle_dist,
			"update"      : self.handle_update,
			"info"        : self.handle_info,
			"search"      : self.handle_search,
			"shell"       : self.handle_shell,
			"provides"    : self.handle_provides,
			"grouplist"   : self.handle_grouplist,
			"repolist"    : self.handle_repolist,
			"clean_all"   : self.handle_clean_all,
			"resolvdep"   : self.handle_resolvdep,
			"cache_create": self.handle_cache_create,
			"cache_cleanup": self.handle_cache_cleanup,
		}

	@property
	def pakfire_args(self):
		ret = { "mode" : "builder" }

		if hasattr(self.args, "disable_repo"):
			ret["disable_repos"] = self.args.disable_repo

		if hasattr(self.args, "enable_repo"):
			ret["enable_repos"] = self.args.enable_repo

		if hasattr(self.args, "offline"):
			ret["offline"] = self.args.offline

		return ret

	def parse_command_update(self):
		# Implement the "update" command.
		sub_update = self.sub_commands.add_parser("update",
			help=_("Update the package indexes."))
		sub_update.add_argument("action", action="store_const", const="update")

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
		sub_build.add_argument("--after-shell", action="store_true",
			help=_("Run a shell after a successful build."))
		sub_build.add_argument("--no-install-test", action="store_true",
			help=_("Do not perform the install test."))

	def parse_command_shell(self):
		# Implement the "shell" command.
		sub_shell = self.sub_commands.add_parser("shell",
			help=_("Go into a shell."))
		sub_shell.add_argument("package", nargs="?",
			help=_("Give name of a package."))
		sub_shell.add_argument("action", action="store_const", const="shell")

		sub_shell.add_argument("-a", "--arch",
			help=_("Emulated architecture in the shell."))
		sub_shell.add_argument("-m", "--mode", nargs="?", default="development",
			help=_("Mode to run in. Is either 'release' or 'development' (default)."))

	def parse_command_dist(self):
		# Implement the "dist" command.
		sub_dist = self.sub_commands.add_parser("dist",
			help=_("Generate a source package."))
		sub_dist.add_argument("package", nargs="+",
			help=_("Give name(s) of a package(s)."))
		sub_dist.add_argument("action", action="store_const", const="dist")

		sub_dist.add_argument("--resultdir", nargs="?",
			help=_("Path were the output files should be copied to."))

	def parse_command_cache(self):
		# Implement the "cache" command.
		sub_cache = self.sub_commands.add_parser("cache",
			help=_("Create a build environment cache."))

		# Implement subcommands.
		sub_cache_commands = sub_cache.add_subparsers()

                self.parse_command_cache_create(sub_cache_commands)
                self.parse_command_cache_cleanup(sub_cache_commands)

	def parse_command_cache_create(self, sub_commands):
		sub_create = sub_commands.add_parser("create",
			help=_("Create a new build environment cache."))
		sub_create.add_argument("action", action="store_const", const="cache_create")

	def parse_command_cache_cleanup(self, sub_commands):
		sub_cleanup = sub_commands.add_parser("cleanup",
			help=_("Remove all cached build environments."))
		sub_cleanup.add_argument("action", action="store_const", const="cache_cleanup")

	def handle_info(self):
		Cli.handle_info(self, long=True)

	def handle_build(self):
		# Get the package descriptor from the command line options
		pkg = self.args.package[0]

		# Check, if we got a regular file
		if os.path.exists(pkg):
			pkg = os.path.abspath(pkg)

		else:
			raise FileNotFoundError, pkg

		# Check whether to enable the install test.
		install_test = not self.args.no_install_test

		pakfire.build(pkg, builder_mode=self.args.mode, install_test=install_test,
			arch=self.args.arch, resultdirs=[self.args.resultdir,],
			shell=True, after_shell=self.args.after_shell, **self.pakfire_args)

	def handle_shell(self):
		pkg = None

		# Get the package descriptor from the command line options
		if self.args.package:
			pkg = self.args.package

			# Check, if we got a regular file
			if os.path.exists(pkg):
				pkg = os.path.abspath(pkg)

			else:
				raise FileNotFoundError, pkg

		pakfire.shell(pkg, builder_mode=self.args.mode,
			arch=self.args.arch, **self.pakfire_args)

	def handle_dist(self):
		# Get the packages from the command line options
		pkgs = []

		for pkg in self.args.package:
			# Check, if we got a regular file
			if os.path.exists(pkg):
				pkg = os.path.abspath(pkg)
				pkgs.append(pkg)

			else:
				raise FileNotFoundError, pkg

		# Put packages to where the user said or our
		# current working directory.
		resultdir = self.args.resultdir or os.getcwd()

		# Change the default pakfire configuration, because
		# packaging source packages can be done in server mode.
		pakfire_args = self.pakfire_args
		pakfire_args["mode"] = "server"

		for pkg in pkgs:
			pakfire.dist(pkg, resultdir=resultdir, **pakfire_args)

	def handle_provides(self):
		pkgs = pakfire.provides(self.args.pattern, **self.pakfire_args)

		for pkg in pkgs:
			print pkg.dump(long=True)

	def handle_cache_create(self):
		pakfire.cache_create(**self.pakfire_args)

	def handle_cache_cleanup(self):
		for env in os.listdir(CACHE_ENVIRON_DIR):
			if not env.endswith(".cache"):
				continue

			print _("Removing environment cache file: %s..." % env)
			env = os.path.join(CACHE_ENVIRON_DIR, env)

			try:
				os.unlink(env)
			except OSError:
				print _("Could not remove file: %s") % env


class CliServer(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire server command line interface."),
		)

		self.parse_common_arguments()

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_build()
		self.parse_command_keepalive()
		self.parse_command_repoupdate()
		self.parse_command_repo()
		self.parse_command_info()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.server = server.Server(**self.pakfire_args)

		self.action2func = {
			"build"      : self.handle_build,
			"info"       : self.handle_info,
			"keepalive"  : self.handle_keepalive,
			"repoupdate" : self.handle_repoupdate,
			"repo_create": self.handle_repo_create,
		}

	@property
	def pakfire_args(self):
		ret = { "mode" : "server" }

		if hasattr(self.args, "offline"):
			ret["offline"] = self.args.offline

		return ret

	def parse_command_build(self):
		# Implement the "build" command.
		sub_build = self.sub_commands.add_parser("build",
			help=_("Send a scrach build job to the server."))
		sub_build.add_argument("package", nargs=1,
			help=_("Give name of at least one package to build."))
		sub_build.add_argument("--arch", "-a",
			help=_("Limit build to only these architecture(s)."))
		sub_build.add_argument("action", action="store_const", const="build")

	def parse_command_keepalive(self):
		# Implement the "keepalive" command.
		sub_keepalive = self.sub_commands.add_parser("keepalive",
			help=_("Send a keepalive to the server."))
		sub_keepalive.add_argument("action", action="store_const",
			const="keepalive")

	def parse_command_repoupdate(self):
		# Implement the "repoupdate" command.
		sub_repoupdate = self.sub_commands.add_parser("repoupdate",
			help=_("Update all repositories."))
		sub_repoupdate.add_argument("action", action="store_const",
			const="repoupdate")

	def parse_command_repo(self):
		sub_repo = self.sub_commands.add_parser("repo",
			help=_("Repository management commands."))

		sub_repo_commands = sub_repo.add_subparsers()

		self.parse_command_repo_create(sub_repo_commands)

	def parse_command_repo_create(self, sub_commands):
		sub_create = sub_commands.add_parser("create",
			help=_("Create a new repository index."))
		sub_create.add_argument("path", nargs=1,
			help=_("Path to the packages."))
		sub_create.add_argument("inputs", nargs="+",
			help=_("Path to input packages."))
		sub_create.add_argument("--key", "-k", nargs="?",
			help=_("Key to sign the repository with."))
		sub_create.add_argument("action", action="store_const", const="repo_create")

	def parse_command_info(self):
		sub_info = self.sub_commands.add_parser("info",
			help=_("Dump some information about this machine."))
		sub_info.add_argument("action", action="store_const", const="info")

	def handle_keepalive(self):
		self.server.update_info()

	def handle_build(self):
		# Arch.
		if self.args.arch:
			arches = self.args.arch.split()

		(package,) = self.args.package

		self.server.create_scratch_build({})
		return

		# Temporary folter for source package.
		tmpdir = "/tmp/pakfire-%s" % util.random_string()

		try:
			os.makedirs(tmpdir)

			pakfire.dist(package, resultdir=[tmpdir,])

			for file in os.listdir(tmpdir):
				file = os.path.join(tmpdir, file)

				print file

		finally:
			if os.path.exists(tmpdir):
				util.rm(tmpdir)

	def handle_repoupdate(self):
		self.server.update_repositories()

	def handle_repo_create(self):
		path = self.args.path[0]

		pakfire.repo_create(path, self.args.inputs, key_id=self.args.key,
			**self.pakfire_args)

	def handle_info(self):
		info = self.server.info()

		print "\n".join(info)


class CliBuilderIntern(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire builder command line interface."),
		)

		self.parse_common_arguments()

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

	def handle_build(self):
		# Get the package descriptor from the command line options
		pkg = self.args.package[0]

		# Check, if we got a regular file
		if os.path.exists(pkg):
			pkg = os.path.abspath(pkg)
		else:
			raise FileNotFoundError, pkg

		conf = config.ConfigBuilder()

		if self.args.nodeps:
			disable_repos = ["*"]
		else:
			disable_repos = None

		kwargs = {
			"arch"          : self.args.arch,
			"builder_mode"  : self.args.mode,
			"config"        : conf,
			"disable_repos" : disable_repos,
			"resultdir"     : self.args.resultdir,
		}

		pakfire._build(pkg, **kwargs)


class CliClient(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire client command line interface."),
		)

		self.parse_common_arguments(repo_manage_switches=True, offline_switch=True)

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_build()
		self.parse_command_connection_check()
		self.parse_command_info()
		self.parse_command_jobs()
		self.parse_command_builds()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.action2func = {
			"build"       : self.handle_build,
			"conn-check"  : self.handle_connection_check,
			"info"        : self.handle_info,
			"jobs_show"   : self.handle_jobs_show,
			"jobs_active" : self.handle_jobs_active,
			"jobs_latest" : self.handle_jobs_latest,
			"builds_show" : self.handle_builds_show,
		}

		# Read configuration for the pakfire client.
		self.conf = conf = config.ConfigClient()

		# Create connection to pakfire hub.
		self.client = client.PakfireUserClient(
			conf.get("client", "server"),
			conf.get("client", "username"),
			conf.get("client", "password"),
		)

	def parse_command_build(self):
		# Parse "build" command.
		sub_build = self.sub_commands.add_parser("build",
			help=_("Build a package remotely."))
		sub_build.add_argument("package", nargs=1,
			help=_("Give name of a package to build."))
		sub_build.add_argument("action", action="store_const", const="build")

		sub_build.add_argument("-a", "--arch",
			help=_("Build the package for the given architecture."))

	def parse_command_info(self):
		# Implement the "info" command.
		sub_info = self.sub_commands.add_parser("info",
			help=_("Print some information about this host."))
		sub_info.add_argument("action", action="store_const", const="info")

	def parse_command_connection_check(self):
		# Implement the "conn-check" command.
		sub_conn_check = self.sub_commands.add_parser("conn-check",
			help=_("Check the connection to the hub."))
		sub_conn_check.add_argument("action", action="store_const", const="conn-check")

	def parse_command_jobs(self):
		sub_jobs = self.sub_commands.add_parser("jobs",
			help=_("Show information about build jobs."))

		sub_jobs_commands = sub_jobs.add_subparsers()

		self.parse_command_jobs_active(sub_jobs_commands)
		self.parse_command_jobs_latest(sub_jobs_commands)
		self.parse_command_jobs_show(sub_jobs_commands)

	def parse_command_jobs_active(self, sub_commands):
		sub_active = sub_commands.add_parser("active",
			help=_("Show a list of all active jobs."))
		sub_active.add_argument("action", action="store_const", const="jobs_active")

	def parse_command_jobs_latest(self, sub_commands):
		sub_latest = sub_commands.add_parser("latest",
			help=_("Show a list of all recently finished of failed build jobs."))
		sub_latest.add_argument("action", action="store_const", const="jobs_latest")

	def parse_command_jobs_show(self, sub_commands):
		sub_show = sub_commands.add_parser("show",
			help=_("Show details about given build job."))
		sub_show.add_argument("job_id", nargs=1, help=_("The ID of the build job."))
		sub_show.add_argument("action", action="store_const", const="jobs_show")

	def parse_command_builds(self):
		sub_builds = self.sub_commands.add_parser("builds",
			help=_("Show information about builds."))

		sub_builds_commands = sub_builds.add_subparsers()

		self.parse_command_builds_show(sub_builds_commands)

	def parse_command_builds_show(self, sub_commands):
		sub_show = sub_commands.add_parser("show",
			help=_("Show details about the given build."))
		sub_show.add_argument("build_id", nargs=1, help=_("The ID of the build."))
		sub_show.add_argument("action", action="store_const", const="builds_show")

	def handle_build(self):
		(package,) = self.args.package

		# XXX just for now, we do only upload source pfm files.
		assert os.path.exists(package)

		# Create a temporary directory.
		temp_dir = tempfile.mkdtemp()

		try:
			if package.endswith(".%s" % MAKEFILE_EXTENSION):
				pakfire_args = { "mode" : "server" }

				# Create a source package from the makefile.
				package = pakfire.dist(package, temp_dir, **pakfire_args)

			elif package.endswith(".%s" % PACKAGE_EXTENSION):
				pass

			else:
				raise Exception, "Unknown filetype: %s" % package

			# Format arches.
			if self.args.arch:
				arches = self.args.arch.replace(",", " ")
			else:
				arches = None

			# Create a new build on the server.
			build = self.client.build_create(package, arches=arches)

			# XXX Print the resulting build.
			print build

		finally:
			# Cleanup the temporary directory and all files.
			if os.path.exists(temp_dir):
				shutil.rmtree(temp_dir, ignore_errors=True)

	def handle_info(self):
		ret = []

		ret.append("")
		ret.append("  PAKFIRE %s" % PAKFIRE_VERSION)
		ret.append("")
		ret.append("  %-20s: %s" % (_("Hostname"), system.hostname))
		ret.append("  %-20s: %s" % (_("Pakfire hub"), self.conf.get("client", "server")))
		if self.conf.get("client", "username") and self.conf.get("client", "password"):
			ret.append("  %-20s: %s" % \
				(_("Username"), self.conf.get("client", "username")))
		ret.append("")

		# Hardware information
		ret.append("  %s:" % _("Hardware information"))
		ret.append("      %-16s: %s" % (_("CPU model"), system.cpu_model))
		ret.append("      %-16s: %s" % (_("Memory"),    util.format_size(system.memory)))
		ret.append("")
		ret.append("      %-16s: %s" % (_("Native arch"), system.native_arch))
		if not system.arch == system.native_arch:
			ret.append("      %-16s: %s" % (_("Default arch"), system.arch))

		header = _("Supported arches")
		for arch in system.supported_arches:
			ret.append("      %-16s: %s" % (header, arch))
			header = ""
		ret.append("")

		for line in ret:
			print line

	def handle_connection_check(self):
		ret = []

		address = self.client.get_my_address()
		ret.append("  %-20s: %s" % (_("Your IP address"), address))
		ret.append("")

		authenticated = self.client.check_auth()
		if authenticated:
			ret.append("  %s" % _("You are authenticated to the build service:"))

			user = self.client.get_user_profile()
			assert user, "Could not fetch user infomation"

			keys = [
				("name",       _("User name")),
				("realname",   _("Real name")),
				("email",      _("Email address")),
				("registered", _("Registered")),
			]

			for key, desc in keys:
				ret.append("    %-18s: %s" % (desc, user.get(key)))

		else:
			ret.append(_("You could not be authenticated to the build service."))

		for line in ret:
			print line

	def _print_jobs(self, jobs, heading=None):
		if heading:
			print "%s:" % heading
			print

		for job in jobs:
			line = "  [%(type)8s] %(name)-30s: %(state)s"

			print line % job

		print # Empty line at the end.

	def handle_jobs_active(self):
		jobs = self.client.get_active_jobs()

		if not jobs:
			print _("No ongoing jobs found.")
			return

		self._print_jobs(jobs, _("Active build jobs"))

	def handle_jobs_latest(self):
		jobs = self.client.get_latest_jobs()

		if not jobs:
			print _("No jobs found.")
			return

		self._print_jobs(jobs, _("Recently processed build jobs"))

	def handle_builds_show(self):
		(build_id,) = self.args.build_id

		build = self.client.get_build(build_id)
		if not build:
			print _("A build with ID %s could not be found.") % build_id
			return

		print _("Build: %(name)s") % build

		fmt = "%-14s: %s"
		lines = [
			fmt % (_("State"), build["state"]),
			fmt % (_("Priority"), build["priority"]),
		]

		lines.append("%s:" % _("Jobs"))
		for job in build["jobs"]:
			lines.append("  * [%(uuid)s] %(name)-30s: %(state)s" % job)

		for line in lines:
			print " ", line
		print

	def handle_jobs_show(self):
		(job_id,) = self.args.job_id

		job = self.client.get_job(job_id)
		if not job:
			print _("A job with ID %s could not be found.") % job_id
			return

		builder = None
		if job["builder_id"]:
			builder = self.client.get_builder(job["builder_id"])

		print _("Job: %(name)s") % job

		fmt = "%-14s: %s"
		lines = [
			fmt % (_("State"), job["state"]),
			fmt % (_("Arch"), job["arch"]),
		]

		if builder:
			lines += [
				fmt % (_("Build host"), builder["name"]),
				"",
			]

		lines += [
			fmt % (_("Time created"), job["time_created"]),
			fmt % (_("Time started"), job["time_started"]),
			fmt % (_("Time finished"), job["time_finished"]),
			fmt % (_("Duration"), job["duration"]),
		]

		if job["packages"]:
			lines += ["", "%s:" % _("Packages")]

			for pkg in job["packages"]:
				pkg_lines = [
					"* %(friendly_name)s" % pkg,
					"  %(uuid)s" % pkg,
					"",
				]

				lines += ["  %s" % line for line in pkg_lines]

		for line in lines:
			print " ", line
		print # New line.


class CliDaemon(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire daemon command line interface."),
		)

		self.parse_common_arguments(repo_manage_switches=True, offline_switch=True)

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

	def run(self):
		"""
			Runs the pakfire daemon with provided settings.
		"""
		# Read the configuration file for the daemon.
		conf = config.ConfigDaemon()

		# Create daemon instance.
		d = pakfire.client.PakfireDaemon(
			server   = conf.get("daemon", "server"),
			hostname = conf.get("daemon", "hostname"),
			secret   = conf.get("daemon", "secret"),
		)

		try:
			d.run()

		# We cannot just kill the daemon, it needs a smooth shutdown.
		except (SystemExit, KeyboardInterrupt):
			d.shutdown()


class CliKey(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire key command line interface."),
		)

		self.parse_common_arguments(repo_manage_switches=False,
			offline_switch=True)

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_init()
		self.parse_command_generate()
		self.parse_command_import()
		self.parse_command_export()
		self.parse_command_delete()
		self.parse_command_list()
		self.parse_command_sign()
		self.parse_command_verify()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		# Create a pakfire instance.
		self.pakfire = pakfire.Pakfire(**self.pakfire_args)

		self.action2func = {
			"init"        : self.handle_init,
			"generate"    : self.handle_generate,
			"import"      : self.handle_import,
			"export"      : self.handle_export,
			"delete"      : self.handle_delete,
			"list"        : self.handle_list,
			"sign"        : self.handle_sign,
			"verify"      : self.handle_verify,
		}

	@property
	def pakfire_args(self):
		ret = {
			"mode" : "server",
		}

		return ret

	def parse_command_init(self):
		# Parse "init" command.
		sub_init = self.sub_commands.add_parser("init",
			help=_("Initialize the local keyring."))
		sub_init.add_argument("action", action="store_const", const="init")

	def parse_command_generate(self):
		# Parse "generate" command.
		sub_gen = self.sub_commands.add_parser("generate",
			help=_("Import a key from file."))
		sub_gen.add_argument("--realname", nargs=1,
			help=_("The real name of the owner of this key."))
		sub_gen.add_argument("--email", nargs=1,
			help=_("The email address of the owner of this key."))
		sub_gen.add_argument("action", action="store_const", const="generate")

	def parse_command_import(self):
		# Parse "import" command.
		sub_import = self.sub_commands.add_parser("import",
			help=_("Import a key from file."))
		sub_import.add_argument("filename", nargs=1,
			help=_("Filename of that key to import."))
		sub_import.add_argument("action", action="store_const", const="import")

	def parse_command_export(self):
		# Parse "export" command.
		sub_export = self.sub_commands.add_parser("export",
			help=_("Export a key to a file."))
		sub_export.add_argument("keyid", nargs=1,
			help=_("The ID of the key to export."))
		sub_export.add_argument("filename", nargs=1,
			help=_("Write the key to this file."))
		sub_export.add_argument("action", action="store_const", const="export")

	def parse_command_delete(self):
		# Parse "delete" command.
		sub_del = self.sub_commands.add_parser("delete",
			help=_("Delete a key from the local keyring."))
		sub_del.add_argument("keyid", nargs=1,
			help=_("The ID of the key to delete."))
		sub_del.add_argument("action", action="store_const", const="delete")

	def parse_command_list(self):
		# Parse "list" command.
		sub_list = self.sub_commands.add_parser("list",
			help=_("List all imported keys."))
		sub_list.add_argument("action", action="store_const", const="list")

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

	def handle_init(self):
		# Initialize the keyring...
		pakfire.key_init(**self.pakfire_args)

	def handle_generate(self):
		realname = self.args.realname[0]
		email    = self.args.email[0]

		print _("Generating the key may take a moment...")
		print

		# Generate the key.
		pakfire.key_generate(realname, email, **self.pakfire_args)

	def handle_import(self):
		filename = self.args.filename[0]

		# Simply import the file.
		pakfire.key_import(filename, **self.pakfire_args)

	def handle_export(self):
		keyid    = self.args.keyid[0]
		filename = self.args.filename[0]

		pakfire.key_export(keyid, filename, **self.pakfire_args)

	def handle_delete(self):
		keyid = self.args.keyid[0]

		pakfire.key_delete(keyid, **self.pakfire_args)

	def handle_list(self):
		lines = pakfire.key_list(**self.pakfire_args)

		for line in lines:
			print line

	def handle_sign(self):
		# Get the files from the command line options
		files = []

		for file in self.args.package:
			# Check, if we got a regular file
			if os.path.exists(file):
				file = os.path.abspath(file)
				files.append(file)

			else:
				raise FileNotFoundError, file

		key = self.args.key[0]

		for file in files:
			# Open the package.
			pkg = packages.open(self.pakfire, None, file)

			print _("Signing %s...") % pkg.friendly_name
			pkg.sign(key)

	def handle_verify(self):
		# Get the files from the command line options
		files = []

		for file in self.args.package:
			# Check, if we got a regular file
			if os.path.exists(file) and not os.path.isdir(file):
				file = os.path.abspath(file)
				files.append(file)

		for file in files:
			# Open the package.
			pkg = packages.open(self.pakfire, None, file)

			print _("Verifying %s...") % pkg.friendly_name
			sigs = pkg.verify()

			for sig in sigs:
				key = self.pakfire.keyring.get_key(sig.fpr)
				if key:
					subkey = key.subkeys[0]

					print "  %s %s" % (subkey.fpr[-16:], key.uids[0].uid)
					if sig.validity:
						print "    %s" % _("This signature is valid.")

				else:
					print "  %s <%s>" % (sig.fpr, _("Unknown key"))
					print "    %s" % _("Could not check if this signature is valid.")

				created = datetime.datetime.fromtimestamp(sig.timestamp)
				print "    %s" % _("Created: %s") % created

				if sig.exp_timestamp:
					expires = datetime.datetime.fromtimestamp(sig.exp_timestamp)
					print "    %s" % _("Expires: %s") % expires

			print # Empty line
