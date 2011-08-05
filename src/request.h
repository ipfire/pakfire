
#ifndef PAKFIRE_REQUEST_H
#define PAKFIRE_REQUEST_H

#include <Python.h>

#include <solv/queue.h>

// Sat Request object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Queue _queue;
} RequestObject;

extern PyObject* Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Request_dealloc(RequestObject *self);

extern void _Request_solvable(RequestObject *self, Id what, Id solvable);
extern void _Request_relation(RequestObject *self, Id what, Id relation);
extern void _Request_name(RequestObject *self, Id what, Id provides);

extern PyObject *Request_install_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_install_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_install_name(RequestObject *self, PyObject *args);

extern PyObject *Request_remove_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_remove_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_remove_name(RequestObject *self, PyObject *args);

extern PyObject *Request_update_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_update_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_update_name(RequestObject *self, PyObject *args);

extern PyObject *Request_lock_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_lock_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_lock_name(RequestObject *self, PyObject *args);

extern PyObject *Request_noobsoletes_solvable(RequestObject *self, PyObject *args);
extern PyObject *Request_noobsoletes_relation(RequestObject *self, PyObject *args);
extern PyObject *Request_noobsoletes_name(RequestObject *self, PyObject *args);

extern PyTypeObject RequestType;

#endif
