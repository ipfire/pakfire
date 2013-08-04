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

#ifndef PAKFIRE_SOLVER_H
#define PAKFIRE_SOLVER_H

#include <Python.h>

#include <solv/solver.h>

// Sat Solver object
typedef struct {
    PyObject_HEAD
    Solver *_solver;
} SolverObject;

extern PyObject* Solver_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Solver_dealloc(SolverObject *self);

extern PyObject *Solver_get_flag(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_flag(SolverObject *self, PyObject *args);

extern PyObject *Solver_get_allow_downgrade(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_downgrade(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_allow_archchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_archchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_allow_vendorchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_vendorchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_allow_uninstall(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_uninstall(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_updatesystem(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_updatesystem(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_do_split_provides(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_do_split_provides(SolverObject *self, PyObject *args);

extern PyObject *Solver_solve(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_problems(SolverObject *self, PyObject *args);

extern PyTypeObject SolverType;

#endif
