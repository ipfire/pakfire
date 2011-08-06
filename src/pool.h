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

#ifndef PAKFIRE_POOL_H
#define PAKFIRE_POOL_H

#include <Python.h>

#include <solv/pool.h>

// Sat Pool object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
} PoolObject;

extern PyObject* Pool_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Pool_dealloc(PoolObject *self);
extern PyObject *Pool_add_repo(PoolObject *self, PyObject *args);
extern PyObject *Pool_prepare(PoolObject *self);
extern void _Pool_prepare(Pool *pool);
extern PyObject *Pool_search(PoolObject *self, PyObject *args);
extern PyObject *Pool_set_installed(PoolObject *self, PyObject *args);
extern PyObject *Pool_providers(PoolObject *self, PyObject *args);
extern PyObject *Pool_size(PoolObject *self);

extern PyTypeObject PoolType;

#endif
