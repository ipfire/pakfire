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

#include <solv/transaction.h>

#include "solver.h"
#include "step.h"
#include "transaction.h"

PyTypeObject TransactionType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Transaction",
	tp_basicsize: sizeof(TransactionObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Transaction_new,
	tp_dealloc: (destructor) Transaction_dealloc,
	tp_doc: "Sat Transaction objects",
};

PyObject* Transaction_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	TransactionObject *self;
	SolverObject *solver;

	if (!PyArg_ParseTuple(args, "O", &solver)) {
		/* XXX raise exception */
	}

	self = (TransactionObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_pool = solver->_solver->pool;
		if (self->_pool == NULL) {
			Py_DECREF(self);
			return NULL;
		}

		// Create a new transaction from the solver and order it.
		self->_transaction = solver_create_transaction(solver->_solver);
		transaction_order(self->_transaction, 0);
	}

	return (PyObject *)self;
}

PyObject *Transaction_dealloc(TransactionObject *self) {
	/* XXX need to free self->_transaction */
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Transaction_steps(TransactionObject *self, PyObject *args) {
	PyObject *list = PyList_New(0);

	StepObject *step;
	int i = 0;
	for(; i < self->_transaction->steps.count; i++) {
		step = PyObject_New(StepObject, &StepType);
		step->_transaction = self->_transaction;
		step->_id = self->_transaction->steps.elements[i];

		PyList_Append(list, (PyObject *)step);
	}

	return list;
}

PyObject *Transaction_get_installsizechange(TransactionObject *self) {
	int installsizechange = transaction_calc_installsizechange(self->_transaction);

	return Py_BuildValue("i", installsizechange * 1024);
}
