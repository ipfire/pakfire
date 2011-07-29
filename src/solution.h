
#ifndef PAKFIRE_SOLUTION_H
#define PAKFIRE_SOLUTION_H

#include <Python.h>

#include "solver.h"

// Sat Solution object
typedef struct {
    PyObject_HEAD
    Solver *_solver;
    Id problem_id;
    Id id;
} SolutionObject;

extern PyObject *Solution_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Solution_dealloc(SolutionObject *self);

extern PyObject *Solution_string(SolutionObject *self);

extern PyTypeObject SolutionType;

#endif
