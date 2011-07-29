
#include <Python.h>

#include "config.h"
#include "problem.h"
#include "relation.h"
#include "request.h"
#include "solution.h"
#include "solvable.h"
#include "solver.h"

PyTypeObject ProblemType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Problem",
	tp_basicsize: sizeof(ProblemObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Problem_new,
	tp_dealloc: (destructor) Problem_dealloc,
	tp_doc: "Sat Problem objects",
	tp_str: (reprfunc)Problem_string,
};

PyObject* Problem_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	ProblemObject *self;
	SolverObject *solver;
	RequestObject *request;
	Id problem_id;

	if (!PyArg_ParseTuple(args, "OOi", &solver, &request, &problem_id)) {
		/* XXX raise exception */
		return NULL;
	}

	self = (ProblemObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_pool = request->_pool;
		self->_solver = solver->_solver;
		self->_id = problem_id;

		// Initialize problem information.
		Problem_init(self);
	}

	return (PyObject *)self;
}

PyObject *Problem_dealloc(ProblemObject *self) {
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Problem_init(ProblemObject *self) {
	Id id = solver_findproblemrule(self->_solver, self->_id);

	self->rule = solver_ruleinfo(self->_solver, id, &self->source,
		&self->target, &self->dep);

	Py_RETURN_NONE;
}

PyObject *Problem_get_rule(ProblemObject *self) {
	return Py_BuildValue("i", self->rule);
}

PyObject *Problem_get_source(ProblemObject *self) {
	SolvableObject *solvable;

	if (self->source == ID_NULL)
		Py_RETURN_NONE;

	solvable = PyObject_New(SolvableObject, &SolvableType);
	if (solvable == NULL)
		return NULL;

	solvable->_pool = self->_pool;
	solvable->_id = self->source;

	return (PyObject *)solvable;
}

PyObject *Problem_get_target(ProblemObject *self) {
	SolvableObject *solvable;

	if (self->target == ID_NULL)
		Py_RETURN_NONE;

	solvable = PyObject_New(SolvableObject, &SolvableType);
	if (solvable == NULL)
		return NULL;

	solvable->_pool = self->_pool;
	solvable->_id = self->target;

	return (PyObject *)solvable;
}

PyObject *Problem_get_dep(ProblemObject *self) {
	RelationObject *relation;

	if (self->dep == ID_NULL)
		Py_RETURN_NONE;

	relation = PyObject_New(RelationObject, &RelationType);
	if (relation == NULL)
		return NULL;

	relation->_pool = self->_pool;
	relation->_id = self->dep;

	return (PyObject *)relation;
}

PyObject *Problem_get_solutions(ProblemObject *self) {
	SolutionObject *solution;
	Id s = 0;

	PyObject *list = PyList_New(0);

	while ((s = solver_next_solution(self->_solver, self->_id, s)) != 0) {
		solution = PyObject_New(SolutionObject, &SolutionType);

		solution->_solver = self->_solver;
		solution->problem_id = self->_id;
		solution->id = s;

		PyList_Append(list, (PyObject *)solution);
	}

	return list;
}

PyObject *Problem_string(ProblemObject *self) {
	Pool *pool = self->_pool;
	char s[STRING_SIZE];

	switch (self->rule) {
		case SOLVER_RULE_DISTUPGRADE:
			snprintf(s, STRING_SIZE - 1,
				_("%s does not belong to a distupgrade repository"),
				pool_solvid2str(pool, self->source)
			);
			break;

		case SOLVER_RULE_INFARCH:
			snprintf(s, STRING_SIZE - 1,
				_("%s has inferior architecture"),
				pool_solvid2str(pool, self->source)
			);
			break;

		case SOLVER_RULE_UPDATE:
			snprintf(s, STRING_SIZE - 1,
				_("problem with installed package %s"),
				pool_solvid2str(pool, self->source)
			);
			break;

		case SOLVER_RULE_JOB:
			snprintf(s, STRING_SIZE - 1, _("conflicting requests"));
			break;

		case SOLVER_RULE_JOB_NOTHING_PROVIDES_DEP:
			snprintf(s, STRING_SIZE - 1,
				_("nothing provides requested %s"),
				pool_dep2str(pool, self->dep)
			);
			break;

		case SOLVER_RULE_RPM:
			snprintf(s, STRING_SIZE - 1, _("some dependency problem"));
			break;

		case SOLVER_RULE_RPM_NOT_INSTALLABLE:
			snprintf(s, STRING_SIZE - 1,
				_("package %s is not installable"),
				pool_solvid2str(pool, self->source)
			);
			break;

		case SOLVER_RULE_RPM_NOTHING_PROVIDES_DEP:
			snprintf(s, STRING_SIZE - 1,
				_("nothing provides %s needed by %s"),
				pool_dep2str(pool, self->dep),  pool_solvid2str(pool, self->source)
			);
			break;

		case SOLVER_RULE_RPM_SAME_NAME:
			snprintf(s, STRING_SIZE - 1,
				_("cannot install both %s and %s"),
				pool_dep2str(pool, self->source),  pool_solvid2str(pool, self->target)
			);
			break;

		case SOLVER_RULE_RPM_PACKAGE_CONFLICT:
			snprintf(s, STRING_SIZE - 1,
				_("package %s conflicts with %s provided by %s"),
				pool_solvid2str(pool, self->source), pool_dep2str(pool, self->dep),
				pool_solvid2str(pool, self->target)
			);
			break;

		case SOLVER_RULE_RPM_PACKAGE_OBSOLETES:
			snprintf(s, STRING_SIZE - 1,
				_("package %s obsoletes %s provided by %s"),
				pool_solvid2str(pool, self->source), pool_dep2str(pool, self->dep),
				pool_solvid2str(pool, self->target)
			);
			break;

		case SOLVER_RULE_RPM_INSTALLEDPKG_OBSOLETES:
			snprintf(s, STRING_SIZE - 1,
				_("installed package %s obsoletes %s provided by %s"),
				pool_solvid2str(pool, self->source), pool_dep2str(pool, self->dep),
				pool_solvid2str(pool, self->target)
			);
			break;

		case SOLVER_RULE_RPM_IMPLICIT_OBSOLETES:
			snprintf(s, STRING_SIZE - 1,
				_("package %s implicitely obsoletes %s provided by %s"),
				pool_solvid2str(pool, self->source), pool_dep2str(pool, self->dep),
				pool_solvid2str(pool, self->target)
			);
			break;

		case SOLVER_RULE_RPM_PACKAGE_REQUIRES:
			snprintf(s, STRING_SIZE - 1,
				_("package %s requires %s, but none of the providers can be installed"),
				pool_solvid2str(pool, self->source), pool_dep2str(pool, self->dep)
			);
			break;

		case SOLVER_RULE_RPM_SELF_CONFLICT:
			snprintf(s, STRING_SIZE - 1,
				_("package %s conflicts with %s provided by itself"),
				pool_solvid2str(pool, self->source), pool_dep2str(pool, self->dep)
			);
			break;

		case SOLVER_RULE_UNKNOWN:
		case SOLVER_RULE_FEATURE:
		case SOLVER_RULE_LEARNT:
		case SOLVER_RULE_CHOICE:
			snprintf(s, STRING_SIZE - 1, _("bad rule type"));
			break;

	}

	return Py_BuildValue("s", &s);
}
