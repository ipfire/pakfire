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

#include <pakfire/pakfire.h>

#include "pakfire.h"

static PyObject* Pakfire_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	PakfireObject* self = (PakfireObject *)type->tp_alloc(type, 0);
	if (self) {
		self->pakfire = NULL;
	}

	return (PyObject *)self;
}

static int Pakfire_init(PakfireObject* self, PyObject* args, PyObject* kwds) {
	const char* path = NULL;
    const char* arch = NULL;

	if (!PyArg_ParseTuple(args, "ss", &path, &arch))
		return -1;

    self->pakfire = pakfire_create(path, arch);
    if (!self->pakfire)
        return -1;

	return 0;
}

static void Pakfire_dealloc(PakfireObject* self) {
	if (self->pakfire)
		pakfire_unref(self->pakfire);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject* Pakfire_repr(PakfireObject* self) {
    const char* path = pakfire_get_path(self->pakfire);
    const char* arch = pakfire_get_arch(self->pakfire);

	return PyUnicode_FromFormat("<_pakfire.Pakfire %s (%s)>", path, arch);
}

static PyObject* Pakfire_get_path(PakfireObject* self) {
    const char* path = pakfire_get_path(self->pakfire);

    return PyUnicode_FromString(path);
}

static PyObject* Pakfire_get_arch(PakfireObject* self) {
    const char* arch = pakfire_get_arch(self->pakfire);

    return PyUnicode_FromString(arch);
}

static struct PyMethodDef Pakfire_methods[] = {
	{ NULL },
};

static struct PyGetSetDef Pakfire_getsetters[] = {
	{
		"arch",
		(getter)Pakfire_get_arch,
		NULL,
		NULL,
		NULL
	},
    {
		"path",
		(getter)Pakfire_get_path,
		NULL,
		NULL,
		NULL
	},
    { NULL },
};

PyTypeObject PakfireType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Pakfire",
	tp_basicsize:       sizeof(PakfireObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Pakfire_new,
	tp_dealloc:         (destructor)Pakfire_dealloc,
	tp_init:            (initproc)Pakfire_init,
	tp_doc:             "Pakfire object",
	tp_methods:         Pakfire_methods,
	tp_getset:          Pakfire_getsetters,
	tp_repr:            (reprfunc)Pakfire_repr,
};
