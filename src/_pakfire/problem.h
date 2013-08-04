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

#ifndef PAKFIRE_PROBLEM_H
#define PAKFIRE_PROBLEM_H

#include <Python.h>

#include <solv/pool.h>
#include <solv/solver.h>

// Sat Problem object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Solver *_solver;
    Id _id;

    // problem information
    Id rule;
    Id source;
    Id target;
    Id dep;
} ProblemObject;

extern PyObject *Problem_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Problem_dealloc(ProblemObject *self);

extern PyObject *Problem_init(ProblemObject *self);
extern PyObject *Problem_string(ProblemObject *self);

extern PyObject *Problem_get_rule(ProblemObject *self);
extern PyObject *Problem_get_source(ProblemObject *self);
extern PyObject *Problem_get_target(ProblemObject *self);
extern PyObject *Problem_get_dep(ProblemObject *self);

extern PyObject *Problem_get_solutions(ProblemObject *self);

extern PyTypeObject ProblemType;

#endif
