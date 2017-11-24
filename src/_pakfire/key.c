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

#include <pakfire/key.h>
#include <pakfire/util.h>

#include "key.h"
#include "pakfire.h"

static PyObject* Key_new_core(PyTypeObject* type, PakfireObject* pakfire, PakfireKey key) {
	KeyObject* self = (KeyObject *)type->tp_alloc(type, 0);
	if (self) {
		self->pakfire = pakfire;
		self->key  = key;
	}

	return (PyObject *)self;
}

PyObject* new_key(PakfireObject* pakfire, PakfireKey key) {
	return Key_new_core(&KeyType, pakfire, pakfire_key_ref(key));
}

static PyObject* Key_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	return Key_new_core(type, NULL, NULL);
}

static void Key_dealloc(KeyObject* self) {
	if (self->key)
		pakfire_key_unref(self->key);

	if (self->pakfire)
		Py_DECREF(self->pakfire);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Key_init(KeyObject* self, PyObject* args, PyObject* kwds) {
	PyObject* pakfire;
	const char* fingerprint = NULL;

	if (!PyArg_ParseTuple(args, "O!s", &PakfireType, &pakfire, &fingerprint))
		return -1;

	self->pakfire = (PakfireObject *)pakfire;
	Py_INCREF(self->pakfire);

	self->key = pakfire_key_get(self->pakfire->pakfire, fingerprint);
	if (!self->key)
		return -1;

	return 0;
}

static PyObject* Key_repr(KeyObject* self) {
	const char* fingerprint = pakfire_key_get_fingerprint(self->key);

	return PyUnicode_FromFormat("<_pakfire.Key (%s)>", fingerprint);
}

static PyObject* Key_str(KeyObject* self) {
	char* string = pakfire_key_dump(self->key);

	PyObject* object = PyUnicode_FromString(string);
	pakfire_free(string);

	return object;
}

static PyObject* Key_get_fingerprint(KeyObject* self) {
	const char* fingerprint = pakfire_key_get_fingerprint(self->key);

	return PyUnicode_FromString(fingerprint);
}

static PyObject* Key_export(KeyObject* self, PyObject* args) {
	int secret = 0;

	if (!PyArg_ParseTuple(args, "|p", &secret))
		return NULL;

	pakfire_key_export_mode_t mode;
	if (secret)
		mode = PAKFIRE_KEY_EXPORT_MODE_SECRET;
	else
		mode = PAKFIRE_KEY_EXPORT_MODE_PUBLIC;

	// Export the key
	char* export = pakfire_key_export(self->key, mode);

	PyObject* object = PyUnicode_FromFormat("%s", export);
	pakfire_free(export);

	return object;
}

static struct PyMethodDef Key_methods[] = {
	{"export", (PyCFunction)Key_export, METH_VARARGS, NULL},
	{ NULL },
};

static struct PyGetSetDef Key_getsetters[] = {
	{
		"fingerprint",
		(getter)Key_get_fingerprint,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

PyTypeObject KeyType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Key",
	tp_basicsize:       sizeof(KeyObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Key_new,
	tp_dealloc:         (destructor)Key_dealloc,
	tp_init:            (initproc)Key_init,
	tp_doc:             "Key object",
	tp_methods:         Key_methods,
	tp_getset:          Key_getsetters,
	tp_repr:            (reprfunc)Key_repr,
	tp_str:             (reprfunc)Key_str,
};
