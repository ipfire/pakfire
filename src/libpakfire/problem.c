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

#include <pakfire/constants.h>
#include <pakfire/i18n.h>
#include <pakfire/private.h>
#include <pakfire/problem.h>
#include <pakfire/request.h>
#include <pakfire/solution.h>
#include <pakfire/util.h>

static char* to_string(PakfireProblem problem) {
	Solver* solver = problem->request->solver;
	Pool* pool = solver->pool;

	// Get the problem rule
	Id rule = solver_findproblemrule(solver, problem->id);

	// Extract some information about that rule
	Id dep;
	Id source;
	Id target;

	SolverRuleinfo type = solver_ruleinfo(solver, rule, &source, &target, &dep);

	char s[STRING_SIZE];
	switch (type) {
		case SOLVER_RULE_DISTUPGRADE:
			snprintf(s, STRING_SIZE - 1,
				_("%s does not belong to a distupgrade repository"),
				pool_solvid2str(pool, source)
			);
			break;

		case SOLVER_RULE_INFARCH:
			snprintf(s, STRING_SIZE - 1,
				_("%s has inferior architecture"),
				pool_solvid2str(pool, source)
			);
			break;

		case SOLVER_RULE_UPDATE:
			snprintf(s, STRING_SIZE - 1,
				_("problem with installed package %s"),
				pool_solvid2str(pool, source)
			);
			break;

		case SOLVER_RULE_JOB:
			snprintf(s, STRING_SIZE - 1, _("conflicting requests"));
			break;

		case SOLVER_RULE_JOB_UNSUPPORTED:
			snprintf(s, STRING_SIZE - 1, _("unsupported request"));

		case SOLVER_RULE_JOB_NOTHING_PROVIDES_DEP:
			snprintf(s, STRING_SIZE - 1,
				_("nothing provides requested %s"),
				pool_dep2str(pool, dep)
			);
			break;

		case SOLVER_RULE_JOB_UNKNOWN_PACKAGE:
			snprintf(s, STRING_SIZE - 1, _("package %s does not exist"),
				pool_dep2str(pool, dep)
			);
			break;

		case SOLVER_RULE_JOB_PROVIDED_BY_SYSTEM:
			snprintf(s, STRING_SIZE - 1, _("%s is provided by the system"),
				pool_dep2str(pool, dep)
			);
			break;

		case SOLVER_RULE_RPM:
			snprintf(s, STRING_SIZE - 1, _("some dependency problem"));
			break;

		case SOLVER_RULE_BEST:
			if (source > 0)
				snprintf(s, STRING_SIZE - 1,
					_("cannot install the best update candidate for package %s"),
					pool_solvid2str(pool, source)
				);
			else
				snprintf(s, STRING_SIZE - 1, _("cannot install the best candidate for the job"));
			break;

		case SOLVER_RULE_RPM_NOT_INSTALLABLE:
			snprintf(s, STRING_SIZE - 1,
				_("package %s is not installable"),
				pool_solvid2str(pool, source)
			);
			break;

		case SOLVER_RULE_RPM_NOTHING_PROVIDES_DEP:
			snprintf(s, STRING_SIZE - 1,
				_("nothing provides %s needed by %s"),
				pool_dep2str(pool, dep),  pool_solvid2str(pool, source)
			);
			break;

		case SOLVER_RULE_RPM_SAME_NAME:
			snprintf(s, STRING_SIZE - 1,
				_("cannot install both %s and %s"),
				pool_solvid2str(pool, source),  pool_solvid2str(pool, target)
			);
			break;

		case SOLVER_RULE_RPM_PACKAGE_CONFLICT:
			snprintf(s, STRING_SIZE - 1,
				_("package %s conflicts with %s provided by %s"),
				pool_solvid2str(pool, source), pool_dep2str(pool, dep),
				pool_solvid2str(pool, target)
			);
			break;

		case SOLVER_RULE_RPM_PACKAGE_OBSOLETES:
			snprintf(s, STRING_SIZE - 1,
				_("package %s obsoletes %s provided by %s"),
				pool_solvid2str(pool, source), pool_dep2str(pool, dep),
				pool_solvid2str(pool, target)
			);
			break;

		case SOLVER_RULE_RPM_INSTALLEDPKG_OBSOLETES:
			snprintf(s, STRING_SIZE - 1,
				_("installed package %s obsoletes %s provided by %s"),
				pool_solvid2str(pool, source), pool_dep2str(pool, dep),
				pool_solvid2str(pool, target)
			);
			break;

		case SOLVER_RULE_RPM_IMPLICIT_OBSOLETES:
			snprintf(s, STRING_SIZE - 1,
				_("package %s implicitely obsoletes %s provided by %s"),
				pool_solvid2str(pool, source), pool_dep2str(pool, dep),
				pool_solvid2str(pool, target)
			);
			break;

		case SOLVER_RULE_RPM_PACKAGE_REQUIRES:
			snprintf(s, STRING_SIZE - 1,
				_("package %s requires %s, but none of the providers can be installed"),
				pool_solvid2str(pool, source), pool_dep2str(pool, dep)
			);
			break;

		case SOLVER_RULE_RPM_SELF_CONFLICT:
			snprintf(s, STRING_SIZE - 1,
				_("package %s conflicts with %s provided by itself"),
				pool_solvid2str(pool, source), pool_dep2str(pool, dep)
			);
			break;

		case SOLVER_RULE_YUMOBS:
			snprintf(s, STRING_SIZE - 1,
				_("both package %s and %s obsolete %s"),
				pool_solvid2str(pool, source), pool_solvid2str(pool, target), pool_dep2str(pool, dep)
			);
			break;

		case SOLVER_RULE_UNKNOWN:
		case SOLVER_RULE_FEATURE:
		case SOLVER_RULE_LEARNT:
		case SOLVER_RULE_CHOICE:
			snprintf(s, STRING_SIZE - 1, _("bad rule type"));
			break;

	}

	return pakfire_strdup(s);
}

PAKFIRE_EXPORT PakfireProblem pakfire_problem_create(PakfireRequest request, Id id) {
	PakfireProblem problem = pakfire_calloc(1, sizeof(*problem));

	problem->request = pakfire_request_ref(request);
	problem->id = id;

	// Initialise reference counter
	problem->nrefs = 1;
	problem->next = NULL;

	// Extract information from solver
	problem->string = to_string(problem);

	return problem;
}

PAKFIRE_EXPORT PakfireProblem pakfire_problem_ref(PakfireProblem problem) {
	problem->nrefs++;

	return problem;
}

PAKFIRE_EXPORT void pakfire_problem_free(PakfireProblem problem) {
	if (--problem->nrefs > 0)
		return;

	if (problem->next)
		pakfire_problem_free(problem->next);

	pakfire_request_free(problem->request);

	if (problem->string)
		pakfire_free(problem->string);

	pakfire_free(problem);
}

PAKFIRE_EXPORT PakfireProblem pakfire_problem_next(PakfireProblem problem) {
	return problem->next;
}

PAKFIRE_EXPORT void pakfire_problem_append(PakfireProblem problem, PakfireProblem new_problem) {
	PakfireProblem next;

	// Go to last problem in list
	while ((next = pakfire_problem_next(problem)) != NULL) {
		problem = next;
	}

	problem->next = pakfire_problem_ref(new_problem);
}

PAKFIRE_EXPORT const char* pakfire_problem_to_string(PakfireProblem problem) {
	return problem->string;
}

PAKFIRE_EXPORT PakfireSolution pakfire_problem_get_solutions(PakfireProblem problem) {
	PakfireSolution ret = NULL;

	Id solution = 0;
	while ((solution = solver_next_solution(problem->request->solver, problem->id, solution)) != 0) {
		PakfireSolution s = pakfire_solution_create(problem, solution);

		if (ret)
			pakfire_solution_append(ret, s);
		else
			ret = s;
	}

	return ret;
}
