
#ifndef PAKFIRE_STEP_H
#define PAKFIRE_STEP_H

#include <Python.h>

#include <satsolver/pool.h>
#include <satsolver/transaction.h>

// Sat Step object
typedef struct {
    PyObject_HEAD
    Transaction *_transaction;
    Id _id;
} StepObject;

extern PyObject* Step_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Step_dealloc(StepObject *self);
extern PyObject *Step_get_type(StepObject *self, PyObject *args);
extern PyObject *Step_get_solvable(StepObject *self, PyObject *args);

extern PyTypeObject StepType;

#endif
