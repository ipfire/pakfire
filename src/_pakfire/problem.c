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

#include <Python.h>
#include <assert.h>

#include <pakfire/errno.h>
#include <pakfire/problem.h>

#include "pool.h"
#include "problem.h"
#include "solution.h"

static ProblemObject* Problem_new_core(PyTypeObject* type, PakfireProblem problem) {
	ProblemObject* self = (ProblemObject *)type->tp_alloc(type, 0);
	if (self) {
		self->problem = problem;
	}

	return self;
}

PyObject* new_problem(PakfireProblem problem) {
	ProblemObject* p = Problem_new_core(&ProblemType, problem);

	return (PyObject*)p;
}

static PyObject* Problem_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	ProblemObject* self = Problem_new_core(type, NULL);

	return (PyObject *)self;
}

static void Problem_dealloc(ProblemObject* self) {
	if (self->problem)
		pakfire_problem_free(self->problem);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Problem_init(ProblemObject* self, PyObject* args, PyObject* kwds) {
#if 0
	PyObject* pool;

	if (!PyArg_ParseTuple(args, "O!", &PoolType, &pool))
		return -1;

	self->pool = (PoolObject *)pool;
	Py_INCREF(self->pool);

	self->request = pakfire_request_create(self->pool->pool);
#endif

	return 0;
}

static PyObject* Problem_string(ProblemObject* self) {
	const char* string = pakfire_problem_to_string(self->problem);

	return PyUnicode_FromString(string);
}

static PyObject* Problem_get_solutions(ProblemObject* self) {
	PyObject* list = PyList_New(0);

	PakfireSolution solution = pakfire_problem_get_solutions(self->problem);
	while (solution) {
		PyObject* s = new_solution(solution);
		PyList_Append(list, s);
		Py_DECREF(s);

		solution = pakfire_solution_next(solution);
	}

	return list;
}

static struct PyMethodDef Problem_methods[] = {
	{ NULL }
};

static struct PyGetSetDef Problem_getsetters[] = {
	{
		"solutions",
		(getter)Problem_get_solutions,
		NULL,
		NULL,
		NULL,
	},
	{ NULL },
};

PyTypeObject ProblemType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Problem",
	tp_basicsize:       sizeof(ProblemObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Problem_new,
	tp_dealloc:         (destructor)Problem_dealloc,
	tp_init:            (initproc)Problem_init,
	tp_doc:             "Problem object",
	tp_methods:         Problem_methods,
	tp_getset:          Problem_getsetters,
	tp_str:             (reprfunc)Problem_string,
};
