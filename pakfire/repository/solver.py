#!/usr/bin/python

import logging
import satsolver
import time

from transaction import Transaction

import pakfire.util as util

from pakfire.constants import *
from pakfire.i18n import _

class Solver(object):
	RELATIONS = (
		(">=", satsolver.REL_GE,),
		("<=", satsolver.REL_LE,),
		("=" , satsolver.REL_EQ,),
		("<" , satsolver.REL_LT,),
		(">" , satsolver.REL_GT,),
	)

	def __init__(self, pakfire, repos, arch=None):
		self.pakfire = pakfire
		self.repos = repos

		if not arch:
			arch = self.pakfire.distro.arch

		# Mapping from solver ID to a package.
		self.id2pkg = {}

		# Initialize the pool and set the architecture.
		self.pool = satsolver.Pool()
		self.pool.set_arch(arch)

		# Initialize all repositories.
		self.repos = self.init_repos()

		self.pool.prepare()

	def create_relation(self, s):
		s = str(s)

		if s.startswith("/"):
			return satsolver.Relation(self.pool, s)

		for pattern, type in self.RELATIONS:
			if not pattern in s:
				continue

			name, version = s.split(pattern, 1)

			return satsolver.Relation(self.pool, name, type, version)

		return satsolver.Relation(self.pool, s)

	def init_repos(self):
		repos = []

		for repo in self.repos.enabled:
			solvrepo = self.pool.create_repo(repo.name)
			if repo.name == "installed":
				self.pool.set_installed(solvrepo)

			pb = util.make_progress(_("Loading %s") % repo.name, repo.size)
			i = 0

			for pkg in repo.get_all():
				if pb:
					i += 1
					pb.update(i)

				self.add_package(pkg)

			logging.debug("Initialized new repo '%s' with %s packages." % \
				(solvrepo.name(), solvrepo.size()))

			if pb:
				pb.finish()

			repos.append(solvrepo)

		return repos

	def get_repo(self, name):
		for repo in self.pool.repos():
			if not repo.name() == name:
				continue

			return repo

	def add_package(self, pkg, repo_name=None):
		if not repo_name:
			repo_name = pkg.repo.name

		solvrepo = self.get_repo(repo_name)
		assert solvrepo

		solvable = satsolver.Solvable(solvrepo, str(pkg.name),
			str(pkg.friendly_version), str(pkg.arch))

		# Store the solver's ID.
		self.id2pkg[solvable.id()] = pkg

		# Set vendor.
		solvable.set_vendor(pkg.vendor)

		# Import all requires.
		for req in pkg.requires:
			rel = self.create_relation(req)
			solvable.requires().add(rel)

		# Import all provides.
		for prov in pkg.provides:
			rel = self.create_relation(prov)
			solvable.provides().add(rel)

		# Import all conflicts.
		for conf in pkg.conflicts:
			rel = self.create_relation(conf)
			solvable.conflicts().add(rel)

		# Import all obsoletes.
		for obso in pkg.obsoletes:
			rel = self.create_relation(obso)
			solvable.obsoletes().add(rel)

		# Import all files that are in the package.
		rel = self.create_relation("solvable:filemarker")
		solvable.provides().add(rel)
		for file in pkg.filelist:
			rel = self.create_relation(file)
			solvable.provides().add(rel)

	def create_request(self):
		return self.pool.create_request()

	def solve(self, request, interactive=False):
		solver = self.pool.create_solver()
		solver.set_allow_uninstall(True)

		while True:
			# Save start time.
			time_start = time.time()

			# Acutally run the solver.
			res = solver.solve(request)

			# Log time and status of the solver.
			logging.debug("Solving took %s" % (time.time() - time_start))
			logging.debug("Solver status: %s" % res)

			# If the solver succeeded, we return the transaction and return.
			if res:
				# Return a resulting Transaction.
				return Transaction.from_solver(self.pakfire, self, solver)

			# Solver had an error and we now see what we can do:
			logging.info("The solver returned %s problems." % solver.problems_count())

			# XXX everything after this line is totally broken and does not do its
			# job correctly.
			return

			jobactions = {
				satsolver.INSTALL_SOLVABLE : "install",
				satsolver.UPDATE_SOLVABLE  : "update",
				satsolver.REMOVE_SOLVABLE  : "remove",
			}

			problem_count = 0
			for problem in solver.problems(request):
				problem_count += 1

				# A data structure to store the solution to the key that is
				# the user supposed to press.
				solutionmap = {}

				logging.warning(" Problem %s: %s" % (problem_count, problem))

				solution_count = 0
				for solution in problem.solutions():
					solution_count += 1
					solutionmap[solution_count] = solution

					logging.info("  [%2d]: %s" % (solution_count, solution))

				if not interactive:
					continue

				logging.info("  - %s -" % _("Empty to abort."))

				while True:
					print _("Choose a solution:"),

					ret = raw_input()
					# If the user has entered nothing, we abort the operation.
					if not ret:
						return

					try:
						ret = int(ret)
					except ValueError:
						ret = None

					# Get the selected solution from the map.
					solution = solutionmap.get(ret, None)

					if not solution:
						print _("You have entered an invalid solution. Try again.")
						continue

					else:
						jobs = [e.job() for e in solution.elements()]
						for job in jobs:
							try:
								print jobactions[job.cmd()]
							except KeyError:
								raise Exception, "Unknown action called."
						break

	def solvables2packages(self, solvables):
		pkgs = []

		for solv in solvables:
			pkg = self.id2pkg[solv.id()]
			pkgs.append(pkg)

		return pkgs

	def get_by_provides(self, provides):
		print provides
		provides = self.create_relation(provides)

		pkgs = self.solvables2packages(self.pool.providers(provides))

		return pkgs

	get_by_name = get_by_provides
