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
#include <pakfire/relation.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#include "package.h"
#include "relation.h"

PyObject* new_relation(PyTypeObject* type, PakfireRelation relation) {
	RelationObject* self = (RelationObject *)type->tp_alloc(type, 0);
	if (self) {
		self->relation = pakfire_relation_ref(relation);
	}

	return (PyObject*)self;
}

static PyObject* Relation_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	RelationObject* self = (RelationObject *)type->tp_alloc(type, 0);
	if (self) {
		self->relation = NULL;
	}

	return (PyObject*)self;
}

static void Relation_dealloc(RelationObject* self) {
	pakfire_relation_unref(self->relation);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Relation_init(RelationObject* self, PyObject* args, PyObject* kwds) {
	PakfireObject* pakfire;
	const char* relation;

	if (!PyArg_ParseTuple(args, "O!s", &PakfireType, &pakfire, &relation))
		return -1;

	self->relation = pakfire_relation_create_from_string(pakfire->pakfire, relation);
	if (!self->relation) {
		PyErr_Format(PyExc_ValueError, "No such relation: %s", relation);
		return -1;
	}

	return 0;
}

static long Relation_hash(RelationObject* self) {
	return pakfire_relation_get_id(self->relation);
}

static PyObject* Relation_repr(RelationObject* self) {
	char* relation = pakfire_relation_str(self->relation);

	PyObject* repr = PyUnicode_FromFormat("<_pakfire.Relation %s>", relation);
	pakfire_free(relation);

	return repr;
}

static PyObject* Relation_str(RelationObject* self) {
	char* relation = pakfire_relation_str(self->relation);

	PyObject* str = PyUnicode_FromString(relation);
	pakfire_free(relation);

	return str;
}

static PyObject* Relation_get_providers(RelationObject* self) {
	PakfirePackageList packagelist = pakfire_relation_providers(self->relation);

	PyObject* list = PyList_New(0);
	for (unsigned int i = 0; i < pakfire_packagelist_count(packagelist); i++) {
		PakfirePackage package = pakfire_packagelist_get(packagelist, i);

		PyObject* obj = new_package(&PackageType, package);
		PyList_Append(list, obj);

		pakfire_package_unref(package);
		Py_DECREF(obj);
	}

	pakfire_packagelist_unref(packagelist);

	return list;
}

static struct PyGetSetDef Relation_getsetters[] = {
	{
		"providers",
		(getter)Relation_get_providers,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

PyTypeObject RelationType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Relation",
	tp_basicsize:       sizeof(RelationObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Relation_new,
	tp_dealloc:         (destructor)Relation_dealloc,
	tp_init:            (initproc)Relation_init,
	tp_doc:             "Relation object",
	tp_hash:            (hashfunc)Relation_hash,
	tp_repr:            (reprfunc)Relation_repr,
	tp_str:             (reprfunc)Relation_str,
	tp_getset:          Relation_getsetters,
};
