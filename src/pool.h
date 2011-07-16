
#ifndef PAKFIRE_POOL_H
#define PAKFIRE_POOL_H

#include <Python.h>

#include <satsolver/pool.h>

// Sat Pool object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
} PoolObject;

extern PyObject* Pool_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Pool_dealloc(PoolObject *self);
extern PyObject *Pool_add_repo(PoolObject *self, PyObject *args);
extern PyObject *Pool_prepare(PoolObject *self);
extern void _Pool_prepare(Pool *pool);
extern PyObject *Pool_search(PoolObject *self, PyObject *args);
extern PyObject *Pool_set_installed(PoolObject *self, PyObject *args);
extern PyObject *Pool_providers(PoolObject *self, PyObject *args);
extern PyObject *Pool_size(PoolObject *self);

extern PyTypeObject PoolType;

#endif
