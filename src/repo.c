
#include <stdbool.h>
#include <satsolver/repo_write.h>

#include "pool.h"
#include "repo.h"

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

PyObject *Repo_write(RepoObject *self, PyObject *args) {
	const char *filename;

	if (!PyArg_ParseTuple(args, "s", &filename)) {
		/* XXX raise exception */
	}

	// Prepare the pool and internalize all attributes.
	_Pool_prepare(self->_repo->pool);

	// XXX catch if file cannot be opened
	FILE *fp = fopen(filename, "wb");

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
