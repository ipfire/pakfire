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
#include <fnmatch.h>
#include <solv/poolarch.h>
#include <solv/solver.h>

#include <pakfire/errno.h>
#include <pakfire/pakfire.h>
#include <pakfire/pool.h>
#include <pakfire/repo.h>

#include "constants.h"
#include "pakfire.h"
#include "pool.h"
#include "relation.h"
#include "util.h"

static PyObject* Pool_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	PoolObject* self = (PoolObject *)type->tp_alloc(type, 0);
	if (self) {
		self->pool = NULL;
	}

	return (PyObject *)self;
}

static void Pool_dealloc(PoolObject* self) {
	if (self->pool)
		pakfire_pool_unref(self->pool);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Pool_init(PoolObject* self, PyObject* args, PyObject* kwds) {
	PakfireObject* pakfire = NULL;

	if (!PyArg_ParseTuple(args, "O!", &PakfireType, &pakfire))
		return -1;

	self->pool = pakfire_get_pool(pakfire->pakfire);
	if (!self->pool)
		return -1;

	return 0;
}

PyTypeObject PoolType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Pool",
	tp_basicsize:       sizeof(PoolObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Pool_new,
	tp_dealloc:         (destructor)Pool_dealloc,
	tp_init:            (initproc)Pool_init,
	tp_doc:             "Pool object",
};
