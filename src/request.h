
#ifndef PAKFIRE_REQUEST_H
#define PAKFIRE_REQUEST_H

#include <Python.h>

#include <satsolver/queue.h>

// Sat Request object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Queue _queue;
} RequestObject;

extern PyObject* Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Request_dealloc(RequestObject *self);
extern PyObject *Request_install_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_install_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_install_name(RequestObject *self, PyObject *args);

extern PyTypeObject RequestType;

#endif
