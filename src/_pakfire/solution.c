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
#include <pakfire/solution.h>

#include "pool.h"
#include "solution.h"

static SolutionObject* Solution_new_core(PyTypeObject* type, PakfireSolution solution) {
	SolutionObject* self = (SolutionObject *)type->tp_alloc(type, 0);
	if (self) {
		self->solution = solution;
	}

	return self;
}

PyObject* new_solution(PakfireSolution solution) {
	SolutionObject* s = Solution_new_core(&SolutionType, solution);

	return (PyObject*)s;
}

static PyObject* Solution_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	SolutionObject* self = Solution_new_core(type, NULL);

	return (PyObject *)self;
}

static void Solution_dealloc(SolutionObject* self) {
	pakfire_solution_unref(self->solution);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Solution_init(SolutionObject* self, PyObject* args, PyObject* kwds) {
	return 0;
}

static PyObject* Solution_string(SolutionObject* self) {
	const char* string = pakfire_solution_to_string(self->solution);

	return PyUnicode_FromString(string);
}

PyTypeObject SolutionType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Solution",
	tp_basicsize:       sizeof(SolutionObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Solution_new,
	tp_dealloc:         (destructor)Solution_dealloc,
	tp_init:            (initproc)Solution_init,
	tp_doc:             "Solution object",
	tp_str:             (reprfunc)Solution_string,
};
