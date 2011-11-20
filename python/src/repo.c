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
#include <errno.h>
#include <stdbool.h>
#include <solv/repo.h>
#include <solv/repo_solv.h>
#include <solv/repo_write.h>

#include "config.h"
#include "pool.h"
#include "repo.h"
#include "solvable.h"

PyTypeObject RepoType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Repo",
	tp_basicsize: sizeof(RepoObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Repo_new,
	tp_dealloc: (destructor) Repo_dealloc,
	tp_doc: "Sat Repo objects",
};

PyObject* Repo_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	RepoObject *self;

	PoolObject *pool;
	const char *name;

	if (!PyArg_ParseTuple(args, "Os", &pool, &name)) {
		/* XXX raise exception */
		return NULL;
	}

	assert(pool);
	assert(name);

	self = (RepoObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_repo = repo_create(pool->_pool, name);
		if (self->_repo == NULL) {
			Py_DECREF(self);
			return NULL;
		}
	}

	return (PyObject *)self;
}

PyObject *Repo_dealloc(RepoObject *self) {
	// repo_free(self->_repo, 0);
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Repo_name(RepoObject *self) {
	Repo *repo = self->_repo;

	return Py_BuildValue("s", repo->name);
}

PyObject *Repo_size(RepoObject *self) {
	Repo *repo = self->_repo;

	return Py_BuildValue("i", repo->nsolvables);
}

PyObject *Repo_get_enabled(RepoObject *self) {
	if (self->_repo->disabled == 0) {
		Py_RETURN_TRUE;
	}

	Py_RETURN_FALSE;
}

PyObject *Repo_set_enabled(RepoObject *self, PyObject *args) {
	bool enabled;

	if (!PyArg_ParseTuple(args, "b", &enabled)) {
		/* XXX raise exception */
		return NULL;
	}

	if (enabled == true) {
		self->_repo->disabled = 0;
	} else {
		self->_repo->disabled = 1;
	}

	Py_RETURN_NONE;
}

PyObject *Repo_get_priority(RepoObject *self) {
	return Py_BuildValue("i", self->_repo->priority);
}

PyObject *Repo_set_priority(RepoObject *self, PyObject *args) {
	int priority;

	if (!PyArg_ParseTuple(args, "i", &priority)) {
		/* XXX raise exception */
		return NULL;
	}

	self->_repo->priority = priority;

	Py_RETURN_NONE;
}

PyObject *Repo_write(RepoObject *self, PyObject *args) {
	const char *filename;
	char exception[STRING_SIZE];

	if (!PyArg_ParseTuple(args, "s", &filename)) {
		/* XXX raise exception */
	}

	// Prepare the pool and internalize all attributes.
	_Pool_prepare(self->_repo->pool);

	// XXX catch if file cannot be opened
	FILE *fp = NULL;
	if ((fp = fopen(filename, "wb")) == NULL) {
		snprintf(exception, STRING_SIZE - 1, "Could not open file for writing: %s (%s).",
			filename, strerror(errno));
		PyErr_SetString(PyExc_RuntimeError, exception);
		return NULL;
	}

	repo_write(self->_repo, fp, NULL, NULL, 0);

	fclose(fp);

	Py_RETURN_NONE;
}

PyObject *Repo_read(RepoObject *self, PyObject *args) {
	const char *filename;

	if (!PyArg_ParseTuple(args, "s", &filename)) {
		/* XXX raise exception */
	}

	// XXX catch if file cannot be opened
	FILE *fp = fopen(filename, "rb");

	repo_add_solv(self->_repo, fp);

	fclose(fp);

	Py_RETURN_NONE;
}

PyObject *Repo_internalize(RepoObject *self) {
	repo_internalize(self->_repo);

	Py_RETURN_NONE;
}

PyObject *Repo_clear(RepoObject *self) {
	repo_empty(self->_repo, 1);

	Py_RETURN_NONE;
}

PyObject *Repo_get_all(RepoObject *self) {
	Solvable *s;
	Id p;
	Repo *r = self->_repo;

	PyObject *list = PyList_New(0);

	FOR_REPO_SOLVABLES(r, p, s) {
		SolvableObject *solv;

		solv = PyObject_New(SolvableObject, &SolvableType);
		if (solv == NULL)
			return NULL;

		solv->_pool = self->_repo->pool;
		solv->_id = p;

		PyList_Append(list, (PyObject *)solv);
	}

	Py_INCREF(list);
	return list;
}
