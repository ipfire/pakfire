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

#include "pool.h"
#include "relation.h"

#define REL_NONE 0

PyTypeObject RelationType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Relation",
	tp_basicsize: sizeof(RelationObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Relation_new,
	tp_dealloc: (destructor) Relation_dealloc,
	tp_doc: "Sat Relation objects",
	tp_str: (reprfunc)Relation_string,
};

PyObject* Relation_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	RelationObject *self;
	PoolObject *pool;
	const char *name;
	const char *evr = NULL;
	int flags = 0;

	if (!PyArg_ParseTuple(args, "Os|si", &pool, &name, &evr, &flags)) {
		/* XXX raise exception */
		return NULL;
	}

	Id _name = pool_str2id(pool->_pool, name, 1);

	self = (RelationObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		if (flags == REL_NONE) {
			self->_id = _name;
		} else {
			Id _evr = pool_str2id(pool->_pool, evr, 1);
			self->_id = pool_rel2id(pool->_pool, _name, _evr, flags, 1);
		}

		self->_pool = pool->_pool;
	}

	return (PyObject *)self;
}

PyObject *Relation_dealloc(RelationObject *self) {
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Relation_string(RelationObject *self) {
	return Py_BuildValue("s", pool_dep2str(self->_pool, self->_id));
}
