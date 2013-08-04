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

#ifndef PAKFIRE_STEP_H
#define PAKFIRE_STEP_H

#include <Python.h>

#include <solv/pool.h>
#include <solv/transaction.h>

// Sat Step object
typedef struct {
    PyObject_HEAD
    Transaction *_transaction;
    Id _id;
} StepObject;

extern PyObject* Step_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Step_dealloc(StepObject *self);
extern PyObject *Step_get_type(StepObject *self, PyObject *args);
extern PyObject *Step_get_solvable(StepObject *self, PyObject *args);

extern PyTypeObject StepType;

#endif
