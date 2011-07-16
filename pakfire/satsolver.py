#!/usr/bin/python

import logging

import _pakfire
from _pakfire import *

import transaction

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


class Solver(object):
	def __init__(self, pakfire, pool):
		self.pakfire = pakfire
		self.pool = pool

		self._solver = _pakfire.Solver(self.pool)

	def solve(self, request, update=False, allow_downgrade=False):
		#self._solver.set_allow_uninstall(True)
		self._solver.set_allow_downgrade(allow_downgrade)

		# Configure the solver for an update.
		if update:
			self._solver.set_update_system(True)
			self._solver.set_do_split_provides(True)

		res = self._solver.solve(request)

		logging.debug("Solver status: %s" % res)

		# If the solver succeeded, we return the transaction and return.
		if res:
			# Return a resulting Transaction.
			t = Transaction(self._solver)

			return transaction.Transaction.from_solver(self.pakfire, self, t)

		return res
