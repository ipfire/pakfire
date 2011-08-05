
#ifndef PAKFIRE_RELATION_H
#define PAKFIRE_RELATION_H

#include <Python.h>

#include <solv/pool.h>

// Sat Relation object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Id _id;
} RelationObject;

extern PyObject *Relation_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Relation_dealloc(RelationObject *self);

extern PyObject *Relation_string(RelationObject *self);

extern PyTypeObject RelationType;

#endif
