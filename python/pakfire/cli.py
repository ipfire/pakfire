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
import os
import sys

import logger
import packages
import repository
import server
import util

import pakfire.api as pakfire
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
		self.parse_command_localinstall()
		self.parse_command_remove()
		self.parse_command_info()
		self.parse_command_search()
		self.parse_command_check_update()
		self.parse_command_update()
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
			"localinstall" : self.handle_localinstall,
			"remove"       : self.handle_remove,
			"check_update" : self.handle_check_update,
			"update"       : self.handle_update,
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

		return ret

	def parse_common_arguments(self):
		self.parser.add_argument("--version", action="version",
			version="%(prog)s " + PAKFIRE_VERSION)

		self.parser.add_argument("-v", "--verbose", action="store_true",
			help=_("Enable verbose output."))

		self.parser.add_argument("-c", "--config", nargs="?",
			help=_("Path to a configuration file to load."))

		self.parser.add_argument("--disable-repo", nargs="*", metavar="REPO",
			help=_("Disable a repository temporarily."))

		self.parser.add_argument("--enabled-repo", nargs="*", metavar="REPO",
			help=_("Enable a repository temporarily."))

		self.parser.add_argument("--offline", action="store_true",
			help=_("Run pakfire in offline mode."))

	def parse_command_install(self):
		# Implement the "install" command.
		sub_install = self.sub_commands.add_parser("install",
			help=_("Install one or more packages to the system."))
		sub_install.add_argument("package", nargs="+",
			help=_("Give name of at least one package to install."))
		sub_install.add_argument("action", action="store_const", const="install")

	def parse_command_localinstall(self):
		# Implement the "localinstall" command.
		sub_install = self.sub_commands.add_parser("localinstall",
			help=_("Install one or more packages from the filesystem."))
		sub_install.add_argument("package", nargs="+",
			help=_("Give filename of at least one package."))
		sub_install.add_argument("action", action="store_const", const="localinstall")

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
		sub_resolvdep.add_argument("package", nargs="+",
			help=_("Give name of at least one package to check."))
		sub_resolvdep.add_argument("action", action="store_const", const="resolvdep")

	def run(self):
		action = self.args.action

		if not self.action2func.has_key(action):
			raise

		try:
			func = self.action2func[action]
		except KeyError:
			raise # XXX catch and return better error message

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

	def handle_install(self):
		pakfire.install(self.args.package, **self.pakfire_args)

	def handle_localinstall(self):
		pakfire.localinstall(self.args.package, **self.pakfire_args)

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
		pakfire.resolvdep(self.args.package, **self.pakfire_args)


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

		# Create distribution configuration from command line.
		distro_config = {
			"arch" : self.args.arch,
		}

		pakfire.build(pkg, builder_mode=self.args.mode,
			distro_config=distro_config, resultdirs=[self.args.resultdir,],
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

		# Create distribution configuration from command line.
		distro_config = {
			"arch" : self.args.arch,
		}

		pakfire.shell(pkg, builder_mode=self.args.mode,
			distro_config=distro_config, **self.pakfire_args)

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

		pakfire.dist(pkgs, resultdirs=[self.args.resultdir,],
			**self.pakfire_args)

	def handle_provides(self):
		pkgs = pakfire.provides(self.args.pattern, **self.pakfire_args)

		for pkg in pkgs:
			print pkg.dump(long=True)


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

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.server = server.Server(**self.pakfire_args)

		self.action2func = {
			"build"      : self.handle_build,
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
		sub_keepalive = self.sub_commands.add_parser("build",
			help=_("Request a build job from the server."))
		sub_keepalive.add_argument("action", action="store_const", const="build")

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
		sub_create.add_argument("path", nargs=1, help=_("Path to the packages."))
		sub_create.add_argument("inputs", nargs="+", help=_("Path to input packages."))
		sub_create.add_argument("action", action="store_const", const="repo_create")

	def handle_keepalive(self):
		self.server.update_info()

	def handle_build(self):
		self.server.build_job()

	def handle_repoupdate(self):
		self.server.update_repositories()

	def handle_repo_create(self):
		path = self.args.path[0]

		pakfire.repo_create(path, self.args.inputs, **self.pakfire_args)


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

		# Create distribution configuration from command line.
		distro_config = {
			"arch" : self.args.arch,
		}

		pakfire._build(pkg, builder_mode=self.args.mode,
			distro_config=distro_config, resultdir=self.args.resultdir,
			nodeps=self.args.nodeps, **self.pakfire_args)
