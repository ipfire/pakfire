
#ifndef PAKFIRE_REPO_H
#define PAKFIRE_REPO_H

#include <Python.h>

#include <satsolver/repo.h>

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
extern PyObject *Repo_write(RepoObject *self, PyObject *args);
extern PyObject *Repo_read(RepoObject *self, PyObject *args);

extern PyTypeObject RepoType;

#endif
