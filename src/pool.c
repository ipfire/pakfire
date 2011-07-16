
#include <satsolver/poolarch.h>

#include "config.h"
#include "pool.h"
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

		pool_setarch(self->_pool, arch);
		if (self->_pool == NULL) {
			Py_DECREF(self);
			return NULL;
		}
	}

	return (PyObject *)self;
}

PyObject *Pool_dealloc(PoolObject *self) {
	// pool_free(self->_pool);
	self->ob_type->tp_free((PyObject *)self);
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

	Id r;
	int idx;
	FOR_REPOS(idx, r) {
		repo_internalize(r);
	}
}

PyObject *Pool_size(PoolObject *self) {
	Pool *pool = self->_pool;

	return Py_BuildValue("i", pool->nsolvables);
}

PyObject *Pool_search(PoolObject *self, PyObject *args) {
	Py_RETURN_NONE; /* XXX to be done */
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
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	Id id = pool_str2id(self->_pool, name, 0);

	Pool *pool = self->_pool;
	_Pool_prepare(pool);

	PyObject *list = PyList_New(0);

	Id p, pp;
	SolvableObject *solvable;
	FOR_PROVIDES(p, pp, id) {
		solvable = PyObject_New(SolvableObject, &SolvableType);
		solvable->_pool = self->_pool;
		solvable->_id = p;

		PyList_Append(list, (PyObject *)solvable);
	}

	return list;
}
