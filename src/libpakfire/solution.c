/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2017 Pakfire development team                                 #
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
#############################################################################*/

#include <assert.h>

#include <solv/policy.h>

#include <pakfire/constants.h>
#include <pakfire/i18n.h>
#include <pakfire/logging.h>
#include <pakfire/private.h>
#include <pakfire/problem.h>
#include <pakfire/request.h>
#include <pakfire/solution.h>
#include <pakfire/util.h>

struct _PakfireSolution {
	PakfireProblem problem;
	Id id;
	char** elements;

	PakfireSolution next;
	int nrefs;
};

static void import_elements(PakfireSolution solution) {
	Solver* solver = pakfire_request_get_solver(solution->problem->request);
	Pool* pool = solver->pool;

	// Reserve memory
	unsigned int num = solver_solutionelement_count(solver, solution->problem->id, solution->id);
	char** elements = solution->elements = pakfire_calloc(num + 1, sizeof(*elements));

	Id p;
	Id rp;
	Id element = 0;
	while ((element = solver_next_solutionelement(solver, solution->problem->id, solution->id, element, &p, &rp)) != 0) {
		char line[STRING_SIZE];

		if (p == SOLVER_SOLUTION_JOB || p == SOLVER_SOLUTION_POOLJOB) {
			if (p == SOLVER_SOLUTION_JOB)
				rp += solver->pooljobcnt;

			Id how  = solver->job.elements[rp-1];
			Id what = solver->job.elements[rp];

			// XXX pool_job2str must be localised
			snprintf(line, STRING_SIZE - 1, _("do not ask to %s"),
				pool_job2str(pool, how, what, 0));

		} else if (p == SOLVER_SOLUTION_INFARCH) {
			Solvable* s = pool->solvables + rp;

			if (pool->installed && s->repo == pool->installed)
				snprintf(line, STRING_SIZE - 1, _("keep %s despite the inferior architecture"),
					pool_solvable2str(pool, s));
			else
				snprintf(line, STRING_SIZE - 1, _("install %s despite the inferior architecture"),
					pool_solvable2str(pool, s));

		} else if (p == SOLVER_SOLUTION_DISTUPGRADE) {
			Solvable* s = pool->solvables + rp;

			if (pool->installed && s->repo == pool->installed)
				snprintf(line, STRING_SIZE - 1, _("keep obsolete %s"),
					pool_solvable2str(pool, s));
			else
				snprintf(line, STRING_SIZE - 1, _("install %s"),
					pool_solvable2str(pool, s));

		} else if (p == SOLVER_SOLUTION_BEST) {
			Solvable* s = pool->solvables + rp;

			if (pool->installed && s->repo == pool->installed)
				snprintf(line, STRING_SIZE - 1, _("keep old %s"),
					pool_solvable2str(pool, s));
			else
				snprintf(line, STRING_SIZE - 1, _("install %s despite the old version"),
					pool_solvable2str(pool, s));

		} else if (p > 0 && rp == 0)
			snprintf(line, STRING_SIZE - 1, _("allow deinstallation of %s"),
				pool_solvid2str(pool, p));

		else if (p > 0 && rp > 0)
			snprintf(line, STRING_SIZE - 1, _("allow replacement of %s with %s"),
				pool_solvid2str(pool, p), pool_solvid2str(pool, rp));

		else
			snprintf(line, STRING_SIZE - 1, _("bad solution element"));

		// Save line in elements array
		*elements++ = pakfire_strdup(line);
	}

	// Terminate array
	*elements = NULL;
}

PAKFIRE_EXPORT PakfireSolution pakfire_solution_create(PakfireProblem problem, Id id) {
	PakfireSolution solution = pakfire_calloc(1, sizeof(*solution));
	if (solution) {
		DEBUG("Allocated Solution at %p\n", solution);
		solution->nrefs = 1;

		solution->problem = pakfire_problem_ref(problem);
		solution->id = id;

		// Extract information from solver
		import_elements(solution);
	}

	return solution;
}

PAKFIRE_EXPORT PakfireSolution pakfire_solution_ref(PakfireSolution solution) {
	solution->nrefs++;

	return solution;
}

static void pakfire_solution_free(PakfireSolution solution) {
	if (solution->next)
		pakfire_solution_unref(solution->next);

	pakfire_problem_free(solution->problem);

	if (solution->elements)
		while (*solution->elements)
			pakfire_free(*solution->elements++);

	pakfire_free(solution);
	DEBUG("Released Solution at %p\n", solution);
}

PAKFIRE_EXPORT PakfireSolution pakfire_solution_unref(PakfireSolution solution) {
	if (!solution)
		return NULL;

	if (--solution->nrefs > 0)
		return solution;

	pakfire_solution_free(solution);
	return NULL;
}

PAKFIRE_EXPORT PakfireSolution pakfire_solution_next(PakfireSolution solution) {
	return solution->next;
}

PAKFIRE_EXPORT void pakfire_solution_append(PakfireSolution solution, PakfireSolution new_solution) {
	PakfireSolution next;

	// Go to last problem in list
	while ((next = pakfire_solution_next(solution)) != NULL) {
		solution = next;
	}

	solution->next = pakfire_solution_ref(new_solution);
}

static size_t count_elements_length(PakfireSolution solution) {
	size_t length = 0;

	char** elements = solution->elements;
	while (*elements) {
		length += strlen(*elements++) + 1;
	}

	return length;
}

PAKFIRE_EXPORT char* pakfire_solution_to_string(PakfireSolution solution) {
	// Determine length of output string
	size_t length = count_elements_length(solution);

	// Allocate string
	char s[length];
	char* p = s;

	char** elements = solution->elements;
	while (*elements) {
		// Copy line
		char* e = *elements++;
		while (*e)
			*p++ = *e++;

		// Add newline
		*p++ = '\n';
	}

	// Terminate string
	if (p > s)
		*(p-1) = '\0';

	// Make sure that we wrote the string exactly to
	// the last character
	assert((s + length) == p);

	return pakfire_strdup(s);
}
