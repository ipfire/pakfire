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
import time

import logging
log = logging.getLogger("pakfire")

import filelist
import packages
import transaction
import util
import _pakfire

from constants import *
from i18n import _

# Put some variables into our own namespace, to make them easily accessible
# for code, that imports the satsolver module.
SEARCH_STRING = _pakfire.SEARCH_STRING
SEARCH_FIELS  = _pakfire.SEARCH_FILES
SEARCH_GLOB   = _pakfire.SEARCH_GLOB

Repo     = _pakfire.Repo
Solvable = _pakfire.Solvable
Relation = _pakfire.Relation

class Pool(_pakfire.Pool):
	RELATIONS = (
		(">=", _pakfire.REL_GE,),
		("<=", _pakfire.REL_LE,),
		("=" , _pakfire.REL_EQ,),
		("<" , _pakfire.REL_LT,),
		(">" , _pakfire.REL_GT,),
	)

	def create_relation(self, s):
		assert s

		if isinstance(s, filelist._File):
			return Relation(self, s.name)

		elif s.startswith("/"):
			return Relation(self, s)

		for pattern, type in self.RELATIONS:
			if not pattern in s:
				continue

			name, version = s.split(pattern, 1)
			return Relation(self, name.strip(), version.strip(), type)

		return Relation(self, s)

	def create_request(self, builder=False, install=None, remove=None, update=None, updateall=False):
		request = Request(self)

		# Add multiinstall information.
		for solv in PAKFIRE_MULTIINSTALL:
			request.noobsoletes(solv)

		# Apply all installs.
		for req in self.expand_requires(install):
			request.install(req)

		# Apply all removes.
		for req in self.expand_requires(remove):
			request.remove(req)

		# Apply all updates.
		for req in self.expand_requires(update):
			request.update(req)

		# Configure the request to update all packages
		# if requested.
		if updateall:
			request.updateall()

		# Return the request.
		return request

	def grouplist(self, group):
		pkgs = []

		for solv in self.search(group, _pakfire.SEARCH_SUBSTRING, "solvable:group"):
			pkg = packages.SolvPackage(self, solv)

			if group in pkg.groups and not pkg.name in pkgs:
				pkgs.append(pkg.name)

		return sorted(pkgs)

	def expand_requires(self, requires):
		if requires is None:
			return []

		ret = []
		for req in requires:
			if isinstance(req, packages.BinaryPackage):
				ret.append(req)
				continue

			if isinstance(req, packages.SolvPackage):
				ret.append(req.solvable)
				continue

			assert type(req) == type("a"), req

			# Expand all groups.
			if req.startswith("@"):
				reqs = self.grouplist(req[1:])
			else:
				reqs = [req,]

			for req in reqs:
				req = self.create_relation(req)
				ret.append(req)

		return ret

	def resolvdep(self, pkg, logger=None):
		assert os.path.exists(pkg)

		# Open the package file.
		pkg = packages.open(self, None, pkg)

		# Create a new request.
		request = self.create_request(install=pkg.requires)

		# Add build dependencies if needed.
		if isinstance(pkg, packages.Makefile) or isinstance(pkg, packages.SourcePackage):
			for req in self.expand_requires(BUILD_PACKAGES):
				request.install(req)

		# Solv the request.
		solver = self.solve(request, logger=logger)

		if solver.status:
			return solver

		raise DependencyError, solver.get_problem_string()

	def solve(self, request, interactive=False, logger=None, **kwargs):
		# XXX implement interactive

		if not logger:
			logger = logging.getLogger("pakfire")

		# Create a solver.
		solver = Solver(self, request, logger=logger)

		# Apply configuration to solver.
		for key, val in kwargs.items():
			solver.set(key, val)

		# Do the solving.
		solver.solve()

		# Return the solver so one can do stuff with it...
		return solver


class Request(_pakfire.Request):
	def install(self, what):
		if isinstance(what, Solvable):
			self.install_solvable(what)
			return

		elif isinstance(what, Relation):
			self.install_relation(what)
			return

		elif type(what) == type("string"):
			self.install_name(what)
			return

		raise Exception, "Unknown type"

	def remove(self, what):
		if isinstance(what, Solvable):
			self.remove_solvable(what)
			return

		elif isinstance(what, Relation):
			self.remove_relation(what)
			return

		elif type(what) == type("string"):
			self.remove_name(what)
			return

		raise Exception, "Unknown type"

	def update(self, what):
		if isinstance(what, Solvable):
			self.update_solvable(what)
			return

		elif isinstance(what, Relation):
			self.update_relation(what)
			return

		elif type(what) == type("string"):
			self.update_name(what)
			return

		raise Exception, "Unknown type"

	def lock(self, what):
		if isinstance(what, Solvable):
			self.lock_solvable(what)
			return

		elif isinstance(what, Relation):
			self.lock_relation(what)
			return

		elif type(what) == type("string"):
			self.lock_name(what)
			return

		raise Exception, "Unknown type"

	def noobsoletes(self, what):
		if isinstance(what, Solvable):
			self.noobsoletes_solvable(what)
			return

		elif isinstance(what, Relation):
			self.noobsoletes_relation(what)
			return

		elif type(what) == type("string"):
			self.noobsoletes_name(what)
			return

		raise Exception, "Unknown type"


class Solver(object):
	option2flag = {
		"allow_archchange"   : _pakfire.SOLVER_FLAG_ALLOW_ARCHCHANGE,
		"allow_downgrade"    : _pakfire.SOLVER_FLAG_ALLOW_DOWNGRADE,
		"allow_uninstall"    : _pakfire.SOLVER_FLAG_ALLOW_UNINSTALL,
		"allow_vendorchange" : _pakfire.SOLVER_FLAG_ALLOW_VENDORCHANGE,
		"ignore_recommended" : _pakfire.SOLVER_FLAG_IGNORE_RECOMMENDED,
	}

	def __init__(self, pool, request, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")
		self.logger = logger

		self.pool = pool
		self.request = request
		assert self.request, "Empty request?"

		# Create a new solver.
		self.solver = _pakfire.Solver(self.pool)

		# The status of the solver.
		#   None when the solving was not done, yet.
		#   True when the request could be solved.
		#   False when the request could not be solved.
		self.status = None

		# Time that was needed to solve the request.
		self.time = None

		# Cache the transaction and problems.
		self.__problems = None
		self.__transaction = None

	def set(self, option, value):
		try:
			flag = self.option2flag[option]
		except KeyError:
			raise Exception, "Unknown configuration setting: %s" % option
		self.solver.set_flag(flag, value)

	def get(self, option):
		try:
			flag = self.option2flag[option]
		except KeyError:
			raise Exception, "Unknown configuration setting: %s" % option
		return self.solver.get_flag(flag)

	def solve(self):
		assert self.status is None, "Solver did already solve something."

		# Actually solve the request.
		start_time = time.time()
		self.status = self.solver.solve(self.request)

		# Save the amount of time that was needed to solve the request.
		self.time = time.time() - start_time

		if self.status:
			self.logger.info(_("Dependency solving finished in %.2f ms") % (self.time / 1000))
		else:
			raise DependencyError, self.get_problem_string()

	@property
	def problems(self):
		if self.__problems is None:
			self.__problems = self.solver.get_problems(self.request)

		return self.__problems

	def get_problem_string(self):
		assert self.status is False

		lines = [
			_("The solver returned one problem:", "The solver returned %(num)s problems:",
				len(self.problems)) % { "num" : len(self.problems) },
		]

		i = 0
		for problem in self.problems:
			i += 1

			# Print information about the problem.
			lines.append("  #%d: %s" % (i, problem))

		return "\n".join(lines)


	def DEADCODE(self):
		# If the solver succeeded, we return the transaction and return.
		if res:
			# Return a resulting Transaction.
			t = Transaction(solver)

			return transaction.Transaction.from_solver(self.pakfire, self, t)

		# Do the problem handling...
		problems = solver.get_problems(request)

		logger.info("")
		logger.info(_("The solver returned one problem:", "The solver returned %(num)s problems:",
			len(problems)) % { "num" : len(problems) })

		i = 0
		for problem in problems:
			i += 1

			# Print information about the problem to the user.
			logger.info("  #%d: %s" % (i, problem))

		logger.info("")

		if not interactive:
			return False

		# Ask the user if he or she want to modify the request. If not, just exit.
		if not util.ask_user(_("Do you want to manually alter the request?")):
			return False

		print _("You can now try to satisfy the solver by modifying your request.")

		altered = False
		while True:
			if len(problems) > 1:
				print _("Which problem to you want to resolve?")
				if altered:
					print _("Press enter to try to re-solve the request.")
				print "[1-%s]:" % len(problems),

				answer = raw_input()

				# If the user did not enter anything, we abort immediately.
				if not answer:
					break

				# If the user did type anything else than an integer, we ask
				# again.
				try:
					answer = int(answer)
				except ValueError:
					continue

				# If the user entered an integer outside of range, we ask
				# again.
				try:
					problem = problems[answer - 1]
				except KeyError:
					continue

			else:
				problem = problem[0]

			# Get all solutions.
			solutions = problem.get_solutions()

			if len(solutions) == 1:
				solution = solutions[0]
				print _("    Solution: %s") % solution
				print

				if util.ask_user("Do you accept the solution above?"):
					altered = True
					print "XXX do something"

				continue
			else:
				print _("    Solutions:")
				i = 0
				for solution in solutions:
					i += 1
					print "      #%d: %s" % (i, solution)

				print

		if not altered:
			return False

		# If the request was altered by the user, we try to solve it again
		# and see what happens.
		return self.solve(request, update=update, uninstall=uninstall,
			allow_downgrade=allow_downgrade, interactive=interactive)
