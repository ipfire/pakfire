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

import time

import logging
log = logging.getLogger("pakfire")

import _pakfire
from _pakfire import *
from i18n import _

import transaction
import util

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
	def __init__(self, pakfire, request, logger=None):
		if logger is None:
			logger = logging.getLogger("pakfire")
		self.logger = logger

		self.pakfire = pakfire
		self.pool = self.pakfire.pool

		# Default settings.
		self.settings = {
			# Update all installed packages?
			"update" : False,

			# Allow to uninstall any packages?
			"uninstall" : False,

			# Allow to downgrade any packages?
			"allow_downgrade" : False,

			# Allow packages to change their vendors?
			"allow_vendorchange" : False,

			# Allow packages to change their arch?
			"allow_archchange" : False,

			# Fix system?
			"fix_system" : False,
		}

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

	def set(self, key, value):
		assert self.settings.has_key(key), "Unknown configuration setting: %s" % key
		assert value in (True, False), "Invalid value: %s" % value

		try:
			self.settings[key] = value
		except KeyError:
			pass

	def get(self, key):
		assert self.settings.has_key(key), "Unknown configuration setting: %s" % key

		return self.settings.get(key)

	def solve(self):
		assert self.status is None, "Solver did already solve something."

		# Apply solver configuration.
		self.solver.set_fix_system(self.get("fix_system"))
		self.solver.set_allow_uninstall(self.get("uninstall"))
		self.solver.set_allow_downgrade(self.get("allow_downgrade"))

		# Optionally allow packages to change their vendors.
		# This is not recommended because it may have weird effects.
		self.solver.set_allow_vendorchange(self.get("allow_vendorchange"))

		# Optionally allow packages ot change their architecture.
		self.solver.set_allow_archchange(self.get("allow_archchange"))

		# Configure the solver for an update.
		if self.get("update"):
			solver.set_updatesystem(True)
			solver.set_do_split_provides(True)

		# Actually solve the request.
		start_time = time.time()
		self.status = self.solver.solve(self.request)

		# Save the amount of time that was needed to solve the request.
		self.time = time.time() - start_time

		self.logger.debug("Solver status: %s (%.2f ms)" % (self.status, self.time / 1000))

	@property
	def transaction(self):
		if not self.status is True:
			return

		if self.__transaction is None:
			self.__transaction = \
				transaction.Transaction.from_solver(self.pakfire, self)

		return self.__transaction

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
