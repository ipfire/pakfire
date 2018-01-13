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

#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/transaction.h>

#include "package.h"
#include "step.h"
#include "transaction.h"
#include "util.h"

static TransactionObject* Transaction_new_core(PyTypeObject* type, RequestObject* request) {
	TransactionObject* self = (TransactionObject *)type->tp_alloc(type, 0);
	if (!self)
		return NULL;

	if (request) {
		self->request = request;
		Py_INCREF(self->request);
	}

	self->transaction = NULL;

	return self;
}

PyObject* new_transaction(RequestObject* request, PakfireTransaction trans) {
	TransactionObject* transaction = Transaction_new_core(&TransactionType, request);
	transaction->transaction = trans;

	return (PyObject *)transaction;
}

static PyObject* Transaction_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	TransactionObject* self = Transaction_new_core(type, NULL);

	return (PyObject *)self;
}

static void Transaction_dealloc(TransactionObject* self) {
	if (self->transaction)
		pakfire_transaction_unref(self->transaction);

	Py_XDECREF(self->request);
	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Transaction_init(TransactionObject* self, PyObject* args, PyObject* kwds) {
	RequestObject* request;

	if (!PyArg_ParseTuple(args, "O!", &RequestType, &request))
		return -1;

	self->request = request;
	Py_INCREF(self->request);

	PakfireRequest req = request->request;
	self->transaction = pakfire_request_get_transaction(req);

	// If request has got no transaction, we will create an (empty) new one.
	if (!self->transaction) {
		PakfirePool pool = pakfire_request_pool(req);

		self->transaction = pakfire_transaction_create(pool, NULL);
	}

	return 0;
}

static PyObject* Transaction_iter(TransactionObject* self) {
	TransactionIteratorObject* iterator = PyObject_New(TransactionIteratorObject, &TransactionIteratorType);

	iterator->transaction = self;
	Py_INCREF(iterator->transaction);

	iterator->iterator = 0;

	return (PyObject *)iterator;
}

static PyObject* Transaction_get_installsizechange(TransactionObject* self) {
	long installsizechange = pakfire_transaction_installsizechange(self->transaction);

	return PyLong_FromLong(installsizechange);
}

static PyObject* Transaction_dump(TransactionObject* self) {
	char* string = pakfire_transaction_dump(self->transaction, 80);
	assert(string);

	return PyUnicode_FromString(string);
}

static PyObject* Transaction_run(TransactionObject* self) {
	int r = pakfire_transaction_run(self->transaction);

	if (r) {
		PyErr_SetString(PyExc_RuntimeError, "Could not run transaction");
		return NULL;
	}

	Py_RETURN_NONE;
}


static Py_ssize_t Transaction_len(TransactionObject* self) {
	return pakfire_transaction_count(self->transaction);
}

static struct PyMethodDef Transaction_methods[] = {
	{
		"dump",
		(PyCFunction)Transaction_dump,
		METH_NOARGS,
		NULL
	},
	{
		"run",
		(PyCFunction)Transaction_run,
		METH_NOARGS,
		NULL,
	},
	{ NULL },
};

static struct PyGetSetDef Transaction_getsetters[] = {
	{
		"installsizechange",
		(getter)Transaction_get_installsizechange,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

static PySequenceMethods Transaction_sequence = {
	sq_length:          (lenfunc)Transaction_len,
};

PyTypeObject TransactionType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Transaction",
	tp_basicsize:       sizeof(TransactionObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Transaction_new,
	tp_dealloc:         (destructor)Transaction_dealloc,
	tp_init:            (initproc)Transaction_init,
	tp_doc:             "Transaction object",
	tp_methods:         Transaction_methods,
	tp_getset:          Transaction_getsetters,
	tp_iter:            (getiterfunc)Transaction_iter,
	tp_as_sequence:     &Transaction_sequence,
};

static PyObject* TransactionIterator_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	TransactionIteratorObject* self = (TransactionIteratorObject *)type->tp_alloc(type, 0);

	if (self) {
		self->transaction = NULL;
		self->iterator = 0;
	}

	return (PyObject *)self;
}

static void TransactionIterator_dealloc(TransactionIteratorObject* self) {
	Py_XDECREF(self->transaction);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int TransactionIterator_init(TransactionIteratorObject* self, PyObject* args, PyObject* kwds) {
	TransactionObject* transaction;

	if (!PyArg_ParseTuple(args, "O!", &TransactionType, &transaction))
		return -1;

	self->transaction = transaction;
	Py_INCREF(self->transaction);

	return 0;
}

static PyObject* TransactionIterator_next(TransactionIteratorObject* self) {
	PakfireStep step = pakfire_transaction_get_step(self->transaction->transaction, self->iterator++);
	if (step)
		return new_step(self->transaction, step);

	return NULL;
}

PyTypeObject TransactionIteratorType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.TransactionIterator",
	tp_basicsize:       sizeof(TransactionIteratorObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             TransactionIterator_new,
	tp_dealloc:         (destructor)TransactionIterator_dealloc,
	tp_init:            (initproc)TransactionIterator_init,
	tp_doc:             "TransactionIterator object",
	tp_iternext:        (iternextfunc)TransactionIterator_next,
};
