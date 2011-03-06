#!/usr/bin/python

import argparse
import sys

import packages
import repository
import util

from pakfire import Pakfire

from constants import *
from i18n import _

def ask_user(question):
	"""
		Ask the user the question, he or she can answer with yes or no.

		This function returns True for "yes" and False for "no".
		
		If the software is running in a non-inteactive shell, no question
		is asked at all and the answer is always "yes".
	"""
	if not util.cli_is_interactive():
		return True

	print _("%s [y/N]") % question,
	ret = raw_input()

	return ret in ("y", "Y")


class Cli(object):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire command line interface."),
		)

		self.parse_common_arguments()

		self.parser.add_argument("--instroot", metavar="PATH",
			default="/",
			help=_("The path where pakfire should operate in."))

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_install()
		self.parse_command_localinstall()
		self.parse_command_info()
		self.parse_command_search()
		self.parse_command_update()
		self.parse_command_provides()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		# Create instance of the wonderful pakfire :)
		self.pakfire = Pakfire(
			self.args.instroot,
			configs = [self.args.config],
			disable_repos = self.args.disable_repo,
		)

		self.action2func = {
			"install"      : self.handle_install,
			"localinstall" : self.handle_localinstall,
			"update"       : self.handle_update,
			"info"         : self.handle_info,
			"search"       : self.handle_search,
			"provides"     : self.handle_provides,
		}

	def parse_common_arguments(self):
		self.parser.add_argument("-v", "--verbose", action="store_true",
			help=_("Enable verbose output."))

		self.parser.add_argument("-c", "--config", nargs="?",
			help=_("Path to a configuration file to load."))

		self.parser.add_argument("--disable-repo", nargs="*", metavar="REPO",
			help=_("Disable a repository temporarily."))

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

	def parse_command_update(self):
		# Implement the "update" command.
		sub_update = self.sub_commands.add_parser("update",
			help=_("Update the whole system or one specific package."))
		sub_update.add_argument("package", nargs="*",
			help=_("Give a name of a package to update or leave emtpy for all."))
		sub_update.add_argument("action", action="store_const", const="update")

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
		for pattern in self.args.package:
			pkgs = self.pakfire.repos.get_by_glob(pattern)

			pkgs = packages.PackageListing(pkgs)

			for pkg in pkgs:
				print pkg.dump(long=long)

	def handle_search(self):
		pkgs = self.pakfire.repos.search(self.args.pattern)

		pkgs = packages.PackageListing(pkgs)

		for pkg in pkgs:
			print pkg.dump(short=True)

	def handle_update(self):
		pass

	def handle_install(self, local=False):
		if local:
			repo = repository.FileSystemRepository(self.pakfire)

		pkgs = []
		for pkg in self.args.package:
			if local and os.path.exists(pkg):
				pkg = packages.BinaryPackage(self.pakfire, repo, pkg)

			pkgs.append(pkg)

		self.pakfire.install(pkgs)

	def handle_localinstall(self):
		return self.handle_install(local=True)

	def handle_provides(self):
		pkgs = self.pakfire.provides(self.args.pattern)

		for pkg in pkgs:
			print pkg.dump()


class CliBuilder(Cli):
	def __init__(self):
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

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.pakfire = Pakfire(
			builder = True,
			configs = [self.args.config],
			disable_repos = self.args.disable_repo,
		)

		self.action2func = {
			"build"       : self.handle_build,
			"dist"        : self.handle_dist,
			"update"      : self.handle_update,
			"info"        : self.handle_info,
			"search"      : self.handle_search,
			"shell"       : self.handle_shell,
			"provides"    : self.handle_provides,
		}

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

	def parse_command_shell(self):
		# Implement the "shell" command.
		sub_shell = self.sub_commands.add_parser("shell",
			help=_("Go into a shell."))
		sub_shell.add_argument("package", nargs=1,
			help=_("Give name of a package."))
		sub_shell.add_argument("action", action="store_const", const="shell")

		sub_shell.add_argument("-a", "--arch",
			help=_("Emulated architecture in the shell."))

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
		print self.args
		# Get the package descriptor from the command line options
		pkg = self.args.package[0]

		# Check, if we got a regular file
		if os.path.exists(pkg):
			pkg = os.path.abspath(pkg)

			if pkg.endswith(MAKEFILE_EXTENSION):
				pkg = packages.Makefile(self.pakfire, pkg)

			elif pkg.endswith(PACKAGE_EXTENSION):
				repo = repository.FileSystemRepository(self.pakfire)
				pkg = packages.SourcePackage(self.pakfire, repo, pkg)

		else:
			# XXX walk through the source tree and find a matching makefile
			pass

		self.pakfire.build(pkg, arch=self.args.arch, resultdirs=[self.args.resultdir,])

	def handle_shell(self):
		print self.args
		# Get the package descriptor from the command line options
		pkg = self.args.package[0]

		# Check, if we got a regular file
		if os.path.exists(pkg):
			pkg = os.path.abspath(pkg)

			if pkg.endswith(MAKEFILE_EXTENSION):
				pkg = packages.Makefile(self.pakfire, pkg)

			elif pkg.endswith(PACKAGE_EXTENSION):
				repo = repository.FileSystemRepository(self.pakfire)
				pkg = packages.SourcePackage(self.pakfire, repo, pkg)

		else:
			# XXX walk through the source tree and find a matching makefile
			pass

		self.pakfire.shell(pkg, arch=self.args.arch)

	def handle_dist(self):
		# Get the packages from the command line options
		pkgs = []

		for pkg in self.args.package:
			# Check, if we got a regular file
			if os.path.exists(pkg):
				pkg = os.path.abspath(pkg)

				if pkg.endswith(MAKEFILE_EXTENSION):
					pkg = packages.Makefile(self.pakfire, pkg)
					pkgs.append(pkg)

			else:
				# XXX walk through the source tree and find a matching makefile
				pass

		self.pakfire.dist(pkgs, resultdirs=[self.args.resultdir,])

class CliServer(Cli):
	def __init__(self):
		self.parser = argparse.ArgumentParser(
			description = _("Pakfire server command line interface."),
		)

		self.parse_common_arguments()

		# Add sub-commands.
		self.sub_commands = self.parser.add_subparsers()

		self.parse_command_repo()

		# Finally parse all arguments from the command line and save them.
		self.args = self.parser.parse_args()

		self.pakfire = Pakfire(
			builder = True,
			configs = [self.args.config],
			disable_repos = self.args.disable_repo,
		)

		self.action2func = {
			"repo_create" : self.handle_repo_create,
		}

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

	def handle_repo_create(self):
		path = self.args.path[0]

		self.pakfire.repo_create(path, self.args.inputs)
