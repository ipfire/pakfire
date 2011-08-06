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

#include "pool.h"
#include "problem.h"
#include "request.h"
#include "solver.h"

#include <solv/solverdebug.h>

PyTypeObject SolverType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Solver",
	tp_basicsize: sizeof(SolverObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Solver_new,
	tp_dealloc: (destructor) Solver_dealloc,
	tp_doc: "Sat Solver objects",
};

PyObject* Solver_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	SolverObject *self;

	PoolObject *pool;

	if (!PyArg_ParseTuple(args, "O", &pool)) {
		/* XXX raise exception */
	}

	self = (SolverObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_solver = solver_create(pool->_pool);
		if (self->_solver == NULL) {
			Py_DECREF(self);
			return NULL;
		}
	}

	return (PyObject *)self;
}

PyObject *Solver_dealloc(SolverObject *self) {
	solver_free(self->_solver);
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Solver_get_fix_system(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->fixsystem);
}

PyObject *Solver_set_fix_system(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->fixsystem = val;

	Py_RETURN_NONE;
}

PyObject *Solver_get_allow_downgrade(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->allowdowngrade);
}

PyObject *Solver_set_allow_downgrade(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->allowdowngrade = val;

	Py_RETURN_NONE;
}

PyObject *Solver_get_allow_archchange(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->allowarchchange);
}

PyObject *Solver_set_allow_archchange(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->allowarchchange = val;

	Py_RETURN_NONE;
}

PyObject *Solver_get_allow_vendorchange(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->allowvendorchange);
}

PyObject *Solver_set_allow_vendorchange(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->allowvendorchange = val;

	Py_RETURN_NONE;
}

PyObject *Solver_get_allow_uninstall(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->allowuninstall);
}

PyObject *Solver_set_allow_uninstall(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->allowuninstall = val;

	Py_RETURN_NONE;
}

PyObject *Solver_get_updatesystem(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->updatesystem);
}

PyObject *Solver_set_updatesystem(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->updatesystem = val;

	Py_RETURN_NONE;
}

PyObject *Solver_get_do_split_provides(SolverObject *self, PyObject *args) {
	return Py_BuildValue("i", self->_solver->dosplitprovides);
}

PyObject *Solver_set_do_split_provides(SolverObject *self, PyObject *args) {
	int val;

	if (!PyArg_ParseTuple(args, "i", &val)) {
		/* XXX raise exception */
	}

	self->_solver->dosplitprovides = val;

	Py_RETURN_NONE;
}

PyObject *Solver_solve(SolverObject *self, PyObject *args) {
	RequestObject *request;

	if (!PyArg_ParseTuple(args, "O", &request)) {
		/* XXX raise exception */
	}

	// Make sure, the pool is prepared.
	_Pool_prepare(self->_solver->pool);

	solver_solve(self->_solver, &request->_queue);

#ifdef DEBUG
	solver_printallsolutions(self->_solver);
#endif

	if (self->_solver->problems.count == 0) {
		Py_RETURN_TRUE;
	}

	Py_RETURN_FALSE;
}

PyObject *Solver_get_problems(SolverObject *self, PyObject *args) {
	RequestObject *request;

	if (!PyArg_ParseTuple(args, "O", &request)) {
		/* XXX raise exception */
		return NULL;
	}

	PyObject *list = PyList_New(0);

	ProblemObject *problem;
	Id p = 0;
	while ((p = solver_next_problem(self->_solver, p)) != 0) {
		problem = PyObject_New(ProblemObject, &ProblemType);

		problem->_pool = self->_solver->pool;
		problem->_solver = self->_solver;
		problem->_id = p;
		Problem_init(problem);

		PyList_Append(list, (PyObject *)problem);
	}

	return list;
}
