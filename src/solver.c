
#include "pool.h"
#include "problem.h"
#include "request.h"
#include "solver.h"

#include <satsolver/solverdebug.h>

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

	solver_printallsolutions(self->_solver);

	if (self->_solver->problems.count == 0) {
		Py_RETURN_TRUE;
	}

	Py_RETURN_FALSE;
}

PyObject *Solver_get_problems(SolverObject *self, PyObject *args) {
	RequestObject *request;

	if (!PyArg_ParseTuple(args, "O", &request)) {
		/* XXX raise exception */
	}

	PyObject *list = PyList_New(0);

	ProblemObject *problem;
	int i = 0;
	for(; i < self->_solver->problems.count; i++) {
		problem = PyObject_New(ProblemObject, &ProblemType);
		problem->_solver = self->_solver;
		//problem->_request = request->_request;
		problem->_id = self->_solver->problems.elements[i];

		PyList_Append(list, (PyObject *)problem);
	}

	Py_INCREF(list); // XXX do we need this here?
	return (PyObject *)list;
}
