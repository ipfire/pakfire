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

#ifndef PAKFIRE_REPO_H
#define PAKFIRE_REPO_H

#include <Python.h>

#include <solv/repo.h>

// Sat Repo object
typedef struct {
    PyObject_HEAD
    Repo *_repo;
} RepoObject;

extern PyObject *Repo_dealloc(RepoObject *self);
extern PyObject* Repo_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Repo_name(RepoObject *self);
extern PyObject *Repo_size(RepoObject *self);
extern PyObject *Repo_get_enabled(RepoObject *self);
extern PyObject *Repo_set_enabled(RepoObject *self, PyObject *args);
extern PyObject *Repo_get_priority(RepoObject *self);
extern PyObject *Repo_set_priority(RepoObject *self, PyObject *args);
extern PyObject *Repo_write(RepoObject *self, PyObject *args);
extern PyObject *Repo_read(RepoObject *self, PyObject *args);
extern PyObject *Repo_internalize(RepoObject *self);
extern PyObject *Repo_clear(RepoObject *self);
extern PyObject *Repo_get_all(RepoObject *self);
extern PyObject *Repo_rem_solv(RepoObject *self, PyObject *args);

extern PyTypeObject RepoType;

#endif
