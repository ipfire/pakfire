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
#include "request.h"
#include "solvable.h"

#include <solv/solver.h>

PyTypeObject RequestType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Request",
	tp_basicsize: sizeof(RequestObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Request_new,
	tp_dealloc: (destructor) Request_dealloc,
	tp_doc: "Sat Request objects",
};

PyObject* Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	RequestObject *self;
	PoolObject *pool;

	if (!PyArg_ParseTuple(args, "O", &pool)) {
		/* XXX raise exception */
	}

	self = (RequestObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_pool = pool->_pool;
		if (self->_pool == NULL) {
			Py_DECREF(self);
			return NULL;
		}

		queue_init(&self->_queue);
	}

	return (PyObject *)self;
}

PyObject *Request_dealloc(RequestObject *self) {
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

void _Request_solvable(RequestObject *self, Id what, Id solvable) {
	queue_push2(&self->_queue, what|SOLVER_SOLVABLE|SOLVER_WEAK, solvable);
}

void _Request_relation(RequestObject *self, Id what, Id relation) {
	queue_push2(&self->_queue, what|SOLVER_SOLVABLE_PROVIDES|SOLVER_WEAK, relation);
}

void _Request_name(RequestObject *self, Id what, Id provides) {
	queue_push2(&self->_queue, what|SOLVER_SOLVABLE_NAME|SOLVER_WEAK, provides);
}

PyObject *Request_install_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		return NULL;
	}

	_Request_solvable(self, SOLVER_INSTALL, solv->_id);
	Py_RETURN_NONE;
}

PyObject *Request_install_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		return NULL;
	}

	_Request_relation(self, SOLVER_INSTALL, rel->_id);
	Py_RETURN_NONE;
}

PyObject *Request_install_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		return NULL;
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_INSTALL, _name);

	Py_RETURN_NONE;
}

PyObject *Request_remove_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		return NULL;
	}

	_Request_solvable(self, SOLVER_ERASE, solv->_id);
	Py_RETURN_NONE;
}

PyObject *Request_remove_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		return NULL;
	}

	_Request_relation(self, SOLVER_ERASE, rel->_id);
	Py_RETURN_NONE;
}

PyObject *Request_remove_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		return NULL;
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_ERASE, _name);

	Py_RETURN_NONE;
}

PyObject *Request_update_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		return NULL;
	}

	_Request_solvable(self, SOLVER_UPDATE, solv->_id);
	Py_RETURN_NONE;
}

PyObject *Request_update_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		return NULL;
	}

	_Request_relation(self, SOLVER_UPDATE, rel->_id);
	Py_RETURN_NONE;
}

PyObject *Request_update_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		return NULL;
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_UPDATE, _name);

	Py_RETURN_NONE;
}

PyObject *Request_lock_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		return NULL;
	}

	_Request_solvable(self, SOLVER_LOCK, solv->_id);
	Py_RETURN_NONE;
}

PyObject *Request_lock_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		return NULL;
	}

	_Request_relation(self, SOLVER_LOCK, rel->_id);
	Py_RETURN_NONE;
}

PyObject *Request_lock_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		return NULL;
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_LOCK, _name);

	Py_RETURN_NONE;
}

PyObject *Request_noobsoletes_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		return NULL;
	}

	_Request_solvable(self, SOLVER_NOOBSOLETES, solv->_id);
	Py_RETURN_NONE;
}

PyObject *Request_noobsoletes_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		return NULL;
	}

	_Request_relation(self, SOLVER_NOOBSOLETES, rel->_id);
	Py_RETURN_NONE;
}

PyObject *Request_noobsoletes_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		return NULL;
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_NOOBSOLETES, _name);

	Py_RETURN_NONE;
}

PyObject *Request_updateall(RequestObject *self, PyObject *args) {
	queue_push2(&self->_queue, SOLVER_UPDATE|SOLVER_SOLVABLE_ALL, 0);
	Py_RETURN_NONE;
}

PyObject *Request_distupgrade(RequestObject *self, PyObject *args) {
	queue_push2(&self->_queue, SOLVER_DISTUPGRADE|SOLVER_SOLVABLE_ALL, 0);
	Py_RETURN_NONE;
}

PyObject *Request_verify(RequestObject *self, PyObject *args) {
	queue_push2(&self->_queue, SOLVER_VERIFY|SOLVER_SOLVABLE_ALL, 0);
	Py_RETURN_NONE;
}
