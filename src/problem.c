
#include "problem.h"
#include "request.h"
#include "solver.h"

PyTypeObject ProblemType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Problem",
	tp_basicsize: sizeof(ProblemObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Problem_new,
	tp_dealloc: (destructor) Problem_dealloc,
	tp_doc: "Sat Problem objects",
};

PyObject* Problem_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	ProblemObject *self;

	SolverObject *solver;
	RequestObject *request;
	Id problem_id;

	if (!PyArg_ParseTuple(args, "OOi", &solver, &request, &problem_id)) {
		/* XXX raise exception */
	}

	self = (ProblemObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_solver = solver->_solver;
//		self->_request = request->_request;
		self->_id = problem_id;
	}

	return (PyObject *)self;
}

PyObject *Problem_dealloc(ProblemObject *self) {
	//self->ob_type->tp_free((PyObject *)self);
}
