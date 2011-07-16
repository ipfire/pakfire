
#ifndef PAKFIRE_PROBLEM_H
#define PAKFIRE_PROBLEM_H

#include <Python.h>

#include <satsolver/pool.h>
#include <satsolver/solver.h>

// Sat Step object
typedef struct {
    PyObject_HEAD
    Solver *_solver;
//    Request *_request;
    Id _id;
} ProblemObject;

extern PyObject* Problem_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Problem_dealloc(ProblemObject *self);

extern PyTypeObject ProblemType;

#endif
