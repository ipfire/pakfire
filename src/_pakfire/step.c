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
#include <pakfire/step.h>
#include <pakfire/transaction.h>
#include <pakfire/util.h>

#include "package.h"
#include "step.h"
#include "transaction.h"

static StepObject* Step_new_core(PyTypeObject* type, TransactionObject* transaction) {
	StepObject* self = (StepObject *)type->tp_alloc(type, 0);
	if (!self)
		return NULL;

	if (transaction) {
		self->transaction = transaction;
		Py_INCREF(self->transaction);
	}

	self->step = NULL;

	return self;
}

PyObject* new_step(TransactionObject* transaction, PakfireStep s) {
	StepObject* step = Step_new_core(&StepType, transaction);
	step->step = s;

	return (PyObject *)step;
}

static PyObject* Step_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	StepObject* self = Step_new_core(type, NULL);

	return (PyObject *)self;
}

static void Step_dealloc(StepObject* self) {
	if (self->step)
		pakfire_step_free(self->step);

	Py_XDECREF(self->transaction);
	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Step_init(StepObject* self, PyObject* args, PyObject* kwds) {
	TransactionObject* transaction;
	int index = 0;

	if (!PyArg_ParseTuple(args, "O!i", &TransactionType, &transaction, &index))
		return -1;

	self->transaction = transaction;
	Py_INCREF(self->transaction);

	self->step = pakfire_transaction_get_step(transaction->transaction, index);
	if (!self->step) {
		PyErr_SetString(PyExc_AttributeError, "No such step");
		return -1;
	}

	return 0;
}

static PyObject* Step_repr(StepObject* self) {
	PakfirePackage package = pakfire_step_get_package(self->step);
	char* nevra = pakfire_package_get_nevra(package);

	PyObject* repr = PyUnicode_FromFormat("<_pakfire.Step object type %s, %s>",
		pakfire_step_get_type_string(self->step), nevra);

	pakfire_package_free(package);
	pakfire_free(nevra);

	return repr;
}

static PyObject* Step_get_package(StepObject* self) {
	PakfirePackage package = pakfire_step_get_package(self->step);

	PyObject* obj = new_package(self->transaction->request->pool, pakfire_package_id(package));
	pakfire_package_free(package);

	return obj;
}

static PyObject* Step_get_type(StepObject* self) {
	const char* type = pakfire_step_get_type_string(self->step);

	if (!type)
		Py_RETURN_NONE;

	return PyUnicode_FromString(type);
}

static PyObject* Step_get_downloadsize(StepObject* self) {
	unsigned long long downloadsize = pakfire_step_get_downloadsize(self->step);

	return PyLong_FromUnsignedLongLong(downloadsize);
}

static PyObject* Step_get_installsizechange(StepObject* self) {
	long installsizechange = pakfire_step_get_installsizechange(self->step);

	return PyLong_FromLong(installsizechange);
}

static PyObject* Step_needs_download(StepObject* self) {
	if (pakfire_step_needs_download(self->step))
		Py_RETURN_TRUE;

	Py_RETURN_FALSE;
}

static struct PyGetSetDef Step_getsetters[] = {
	{
		"downloadsize",
		(getter)Step_get_downloadsize,
		NULL,
		NULL,
		NULL
	},
	{
		"installsizechange",
		(getter)Step_get_installsizechange,
		NULL,
		NULL,
		NULL
	},
	{
		"needs_download",
		(getter)Step_needs_download,
		NULL,
		NULL,
		NULL
	},
	{
		"package",
		(getter)Step_get_package,
		NULL,
		NULL,
		NULL
	},
	{
		"type",
		(getter)Step_get_type,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

PyTypeObject StepType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Step",
	tp_basicsize:       sizeof(StepObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Step_new,
	tp_dealloc:         (destructor)Step_dealloc,
	tp_init:            (initproc)Step_init,
	tp_doc:             "Step object",
	tp_repr:            (reprfunc)Step_repr,
	tp_getset:          Step_getsetters,
};
