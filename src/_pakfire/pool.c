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

#include "constants.h"
#include "pool.h"
#include "relation.h"
#include "repo.h"
#include "solvable.h"

PyTypeObject PoolType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Pool",
	tp_basicsize: sizeof(PoolObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Pool_new,
	tp_dealloc: (destructor) Pool_dealloc,
	tp_doc: "Sat Pool objects",
};

// Pool
PyObject* Pool_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	PoolObject *self;
	const char *arch;

	if (!PyArg_ParseTuple(args, "s", &arch)) {
		/* XXX raise exception */
		return NULL;
	}

	self = (PoolObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_pool = pool_create();

#ifdef DEBUG
		// Enable debug messages when DEBUG is defined.
		pool_setdebuglevel(self->_pool, 1);
#endif

		pool_setdisttype(self->_pool, DISTTYPE_RPM);
		pool_setarch(self->_pool, arch);
		if (self->_pool == NULL) {
			Py_DECREF(self);
			return NULL;
		}
	}

	return (PyObject *)self;
}

PyObject *Pool_dealloc(PoolObject *self) {
	pool_free(self->_pool);
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Pool_add_repo(PoolObject *self, PyObject *args) {
	const char *name;
	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	RepoObject *repo;

	repo = PyObject_New(RepoObject, &RepoType);
	if (repo == NULL)
		return NULL;

	return (PyObject *)repo;
}

PyObject *Pool_prepare(PoolObject *self) {
	_Pool_prepare(self->_pool);

	Py_RETURN_NONE;
}

void _Pool_prepare(Pool *pool) {
	pool_addfileprovides(pool);
	pool_createwhatprovides(pool);

	Repo *r;
	int idx;
	FOR_REPOS(idx, r) {
		repo_internalize(r);
	}
}

PyObject *Pool_size(PoolObject *self) {
	Pool *pool = self->_pool;

	return Py_BuildValue("i", pool->nsolvables);
}

PyObject *_Pool_search(Pool *pool, Repo *repo, const char *match, int option, const char *keyname) {
	// Prepare the pool, so we can search in it.
	_Pool_prepare(pool);

	Dataiterator d;
	dataiterator_init(&d, pool, repo, 0,
		keyname && pool ? pool_str2id(pool, keyname, 0) : 0, match, option);

	PyObject *list = PyList_New(0);

	SolvableObject *solvable;
	while (dataiterator_step(&d)) {
		solvable = PyObject_New(SolvableObject, &SolvableType);
		solvable->_pool = pool;
		solvable->_id = d.solvid;

		PyList_Append(list, (PyObject *)solvable);
	}

	dataiterator_free(&d);
	return list;
}

PyObject *Pool_search(PoolObject *self, PyObject *args) {
	const char *match = NULL;
	int option = SEARCH_SUBSTRING;
	const char *keyname = NULL;

	if (!PyArg_ParseTuple(args, "s|is", &match, &option, &keyname)) {
		/* XXX raise exception */
		return NULL;
	}

	return _Pool_search(self->_pool, NULL, match, option, keyname);
}

PyObject *Pool_set_installed(PoolObject *self, PyObject *args) {
	RepoObject *repo;

	if (!PyArg_ParseTuple(args, "O", &repo)) {
		/* XXX raise exception */
	}

	pool_set_installed(self->_pool, repo->_repo);

	Py_RETURN_NONE;
}

PyObject *Pool_providers(PoolObject *self, PyObject *args) {
	char *name = NULL;
	Queue job;
	Solvable *solvable;
	Pool *pool = self->_pool;
	Id p, pp;
	int i;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		return NULL;
	}

	_Pool_prepare(pool);
	queue_init(&job);

	Id id = pool_str2id(pool, name, 0);

	if (id) {
		FOR_PROVIDES(p, pp, id) {
			solvable = pool->solvables + p;

			if (solvable->name == id)
				queue_push2(&job, SOLVER_SOLVABLE, p);
		}
	}

	for (p = 1; p < pool->nsolvables; p++) {
		solvable = pool->solvables + p;
		if (!solvable->repo || !pool_installable(pool, solvable))
			continue;

		id = solvable->name;
		if (fnmatch(name, pool_id2str(pool, id), 0) == 0) {
			for (i = 0; i < job.count; i += 2) {
				if (job.elements[i] == SOLVER_SOLVABLE && job.elements[i + 1] == id)
					break;
			}

			if (i == job.count)
				queue_push2(&job, SOLVER_SOLVABLE, p);
		}
	}

	for (id = 1; id < pool->ss.nstrings; id++) {
		if (!pool->whatprovides[id])
			continue;

		if (fnmatch(name, pool_id2str(pool, id), 0) == 0) {
			Id *provides = pool->whatprovidesdata + pool->whatprovides[id];

			while (*provides) {
				for (i = 0; i < job.count; i += 2) {
					if (job.elements[i] == SOLVER_SOLVABLE && job.elements[i + 1] == *provides)
						break;
				}

				if (i == job.count)
					queue_push2(&job, SOLVER_SOLVABLE, *provides);

				provides++;
			}
		}
	}

	SolvableObject *s;
	PyObject *list = PyList_New(0);

	for (i = 0; i < job.count; i += 2) {
		switch (job.elements[i]) {
			case SOLVER_SOLVABLE:
				s = PyObject_New(SolvableObject, &SolvableType);
				s->_pool = pool;
				s->_id = job.elements[i + 1];

				PyList_Append(list, (PyObject *)s);
		}
	}

	return list;
}
