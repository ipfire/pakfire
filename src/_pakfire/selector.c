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

#include <pakfire/errno.h>
#include <pakfire/filter.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/selector.h>
#include <pakfire/types.h>

#include "package.h"
#include "pakfire.h"
#include "selector.h"

static PyObject* Selector_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	SelectorObject* self = (SelectorObject *)type->tp_alloc(type, 0);
	if (self) {
		self->selector = NULL;
	}

	return (PyObject *)self;
}

static void Selector_dealloc(SelectorObject* self) {
	pakfire_selector_unref(self->selector);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Selector_init(SelectorObject* self, PyObject* args, PyObject* kwds) {
	PakfireObject* pakfire;

	if (!PyArg_ParseTuple(args, "O!", &PakfireType, &pakfire))
		return -1;

	self->selector = pakfire_selector_create(pakfire->pakfire);

	return 0;
}

static PyObject* Selector_set(SelectorObject* self, PyObject* args) {
	int keyname;
	int cmp_type;
	const char* match;

	if (!PyArg_ParseTuple(args, "iis", &keyname, &cmp_type, &match))
		return NULL;

	int ret = pakfire_selector_set(self->selector, keyname, cmp_type, match);

	switch (ret) {
		case PAKFIRE_E_SELECTOR:
			PyErr_SetString(PyExc_ValueError, "Invalid Selector specification");
			return NULL;

		default:
			Py_RETURN_NONE;
	}
}

static PyObject* Selector_get_providers(SelectorObject* self) {
	PakfirePackageList packagelist = pakfire_selector_providers(self->selector);

	PyObject* list = PyList_New(0);
	for (unsigned int i = 0; i < pakfire_packagelist_count(packagelist); i++) {
		PakfirePackage package = pakfire_packagelist_get(packagelist, i);

		PyObject* obj = new_package(NULL, pakfire_package_id(package));
		PyList_Append(list, obj);

		pakfire_package_unref(package);
		Py_DECREF(obj);
	}

	pakfire_packagelist_unref(packagelist);

	return list;
}

static struct PyGetSetDef Selector_getsetters[] = {
	{
		"providers",
		(getter)Selector_get_providers,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

static struct PyMethodDef Selector_methods[] = {
	{
		"set",
		(PyCFunction)Selector_set,
		METH_VARARGS,
		NULL
	},
	{ NULL },
};

PyTypeObject SelectorType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:			"_pakfire.Selector",
	tp_basicsize:		sizeof(SelectorObject),
	tp_flags:			Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:				Selector_new,
	tp_dealloc:			(destructor)Selector_dealloc,
	tp_init:			(initproc)Selector_init,
	tp_doc:				"Selector object",
	tp_methods:			Selector_methods,
	tp_getset:          Selector_getsetters,
};
