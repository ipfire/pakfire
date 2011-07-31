#!/usr/bin/python

import logging

import _pakfire
from _pakfire import *

import transaction
import util

from i18n import _

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


class Solver(object):
	def __init__(self, pakfire, pool):
		self.pakfire = pakfire
		self.pool = pool

	def solve(self, request, update=False, uninstall=False, allow_downgrade=False,
			interactive=False, logger=None):
		# If no logger was provided, we use the root logger.
		if logger is None:
			logger = logging.getLogger()

		# Create a new solver.
		solver = _pakfire.Solver(self.pool)

		solver.set_allow_uninstall(uninstall)
		solver.set_allow_downgrade(allow_downgrade)

		# Configure the solver for an update.
		if update:
			solver.set_updatesystem(True)
			solver.set_do_split_provides(True)

		# Actually solve the request.
		res = solver.solve(request)

		logger.debug("Solver status: %s" % res)

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
