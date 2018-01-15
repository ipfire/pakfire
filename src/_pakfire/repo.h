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

#ifndef PYTHON_PAKFIRE_REPO_H
#define PYTHON_PAKFIRE_REPO_H

#include <Python.h>

#include <pakfire/pool.h>
#include <pakfire/repo.h>

#include "pool.h"

typedef struct {
    PyObject_HEAD
    PoolObject* pool;
    PakfireRepo repo;

	// XXX COMPAT
	void* _repo;
} RepoObject;

extern PyTypeObject RepoType;

PyObject* new_repo(PoolObject* pool, const char* name);

#endif /* PYTHON_PAKFIRE_REPO_H */
