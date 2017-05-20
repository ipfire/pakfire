/*#############################################################################
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
#############################################################################*/

#include <Python.h>

#include <solv/policy.h>
#include <solv/solverdebug.h>

#include "constants.h"
#include "problem.h"
#include "solution.h"

PyTypeObject SolutionType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name: "_pakfire.Solution",
	tp_basicsize: sizeof(SolutionObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new: Solution_new,
	tp_dealloc: (destructor)Solution_dealloc,
	tp_doc: "Sat Solution objects",
	tp_str: (reprfunc)Solution_string,
};

PyObject *Solution_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	SolutionObject *self;
	ProblemObject *problem;
	Id id;

	if (!PyArg_ParseTuple(args, "Oi", &problem, &id)) {
		/* XXX raise exception */
		return NULL;
	}

	self = (SolutionObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
#if 0
		self->_solver = problem->_solver;
		self->problem_id = problem->_id;
#endif
		self->id = id;
	}

	return (PyObject *)self;
}

PyObject *Solution_dealloc(SolutionObject *self) {
	Py_TYPE(self)->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Solution_string(SolutionObject *self) {
	Pool *pool = self->_solver->pool;
	Solver *solver = self->_solver;
	char str[STRING_SIZE];

	Solvable *s, *sd;
	Id p, rp;
	Id how, what, select;

	Id element = 0;
	while ((element = solver_next_solutionelement(solver, self->problem_id, self->id, element, &p, &rp)) != 0) {
		if (p == SOLVER_SOLUTION_JOB) {
			how = solver->job.elements[rp - 1];
			what = solver->job.elements[rp];
			select = how & SOLVER_SELECTMASK;

			switch (how & SOLVER_JOBMASK) {
				case SOLVER_INSTALL:
					if (select == SOLVER_SOLVABLE && pool->installed && pool->solvables[what].repo == pool->installed)
						snprintf(str, STRING_SIZE - 1, _("do not keep %s installed"),
							pool_solvid2str(pool, what));
					else if (select == SOLVER_SOLVABLE_PROVIDES)
						snprintf(str, STRING_SIZE - 1, _("do not install a solvable %s"),
							solver_select2str(pool, select, what));
					else
						snprintf(str, STRING_SIZE - 1, _("do not install %s"),
							solver_select2str(pool, select, what));
					break;

				case SOLVER_ERASE:
					if (select == SOLVER_SOLVABLE && !(pool->installed && pool->solvables[what].repo == pool->installed))
						snprintf(str, STRING_SIZE - 1, _("do not forbid installation of %s"),
							pool_solvid2str(pool, what));
					else if (select == SOLVER_SOLVABLE_PROVIDES)
						snprintf(str, STRING_SIZE - 1, _("do not deinstall all solvables %s"),
							solver_select2str(pool, select, what));
					else
						snprintf(str, STRING_SIZE - 1, _("do not deinstall %s"),
							solver_select2str(pool, select, what));
					break;

				case SOLVER_UPDATE:
					snprintf(str, STRING_SIZE - 1, _("do not install most recent version of %s"),
						solver_select2str(pool, select, what));
					break;

				case SOLVER_LOCK:
					snprintf(str, STRING_SIZE - 1, _("do not lock %s"),
						solver_select2str(pool, select, what));
					break;

				default:
					snprintf(str, STRING_SIZE - 1, _("do something different"));
					break;
			}

		} else if (p == SOLVER_SOLUTION_INFARCH) {
			s = pool->solvables + rp;
			if (pool->installed && s->repo == pool->installed)
				snprintf(str, STRING_SIZE - 1, _("keep %s despite the inferior architecture"),
					pool_solvable2str(pool, s));
			else
				snprintf(str, STRING_SIZE - 1, _("install %s despite the inferior architecture"),
					pool_solvable2str(pool, s));

		} else if (p == SOLVER_SOLUTION_DISTUPGRADE) {
			s = pool->solvables + rp;
			if (pool->installed && s->repo == pool->installed)
				snprintf(str, STRING_SIZE - 1, _("keep obsolete %s"),
					pool_solvable2str(pool, s));
			else
				snprintf(str, STRING_SIZE - 1, _("install %s from excluded repository"),
					pool_solvable2str(pool, s));

		} else {
			s = pool->solvables + p;
			sd = rp ? pool->solvables + rp : 0;

			if (sd) {
				int illegal = policy_is_illegal(solver, s, sd, 0);

				// XXX multiple if clauses can match here
				if ((illegal & POLICY_ILLEGAL_DOWNGRADE) != 0)
					snprintf(str, STRING_SIZE - 1, _("allow downgrade of %s to %s"),
						pool_solvable2str(pool, s), pool_solvable2str(pool, sd));

				if ((illegal & POLICY_ILLEGAL_ARCHCHANGE) != 0)
					snprintf(str, STRING_SIZE - 1, _("allow architecture change of %s to %s"),
						pool_solvable2str(pool, s), pool_solvable2str(pool, sd));

				if ((illegal & POLICY_ILLEGAL_VENDORCHANGE) != 0) {
					if (sd->vendor)
						snprintf(str, STRING_SIZE - 1, _("allow vendor change from '%s' (%s) to '%s' (%s)"),
							pool_id2str(pool, s->vendor), pool_solvable2str(pool, s),
							pool_id2str(pool, sd->vendor), pool_solvable2str(pool, sd));
					else
						snprintf(str, STRING_SIZE - 1, _("allow vendor change from '%s' (%s) to no vendor (%s)"),
							pool_id2str(pool, s->vendor), pool_solvable2str(pool, s),
							pool_solvable2str(pool, sd));
				}

				if (!illegal)
					snprintf(str, STRING_SIZE - 1, _("allow replacement of %s with %s"),
						pool_solvable2str(pool, s), pool_solvable2str(pool, sd));
			}
		}
	}

	return Py_BuildValue("s", &str);
}
