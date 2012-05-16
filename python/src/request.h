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

#ifndef PAKFIRE_REQUEST_H
#define PAKFIRE_REQUEST_H

#include <Python.h>

#include <solv/queue.h>

// Sat Request object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Queue _queue;
} RequestObject;

extern PyObject* Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Request_dealloc(RequestObject *self);

extern void _Request_solvable(RequestObject *self, Id what, Id solvable);
extern void _Request_relation(RequestObject *self, Id what, Id relation);
extern void _Request_name(RequestObject *self, Id what, Id provides);

extern PyObject *Request_install_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_install_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_install_name(RequestObject *self, PyObject *args);

extern PyObject *Request_remove_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_remove_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_remove_name(RequestObject *self, PyObject *args);

extern PyObject *Request_update_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_update_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_update_name(RequestObject *self, PyObject *args);

extern PyObject *Request_lock_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_lock_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_lock_name(RequestObject *self, PyObject *args);

extern PyObject *Request_noobsoletes_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_noobsoletes_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_noobsoletes_name(RequestObject *self, PyObject *args);

extern PyObject *Request_updateall(RequestObject *self, PyObject *args);
extern PyObject *Request_distupgrade(RequestObject *self, PyObject *args);
extern PyObject *Request_verify(RequestObject *self, PyObject *args);

extern PyTypeObject RequestType;

#endif
