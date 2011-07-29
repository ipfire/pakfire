
#ifndef PAKFIRE_PROBLEM_H
#define PAKFIRE_PROBLEM_H

#include <Python.h>

#include <satsolver/pool.h>
#include <satsolver/solver.h>

// Sat Problem object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Solver *_solver;
    Id _id;

    // problem information
    Id rule;
    Id source;
    Id target;
    Id dep;
} ProblemObject;

extern PyObject *Problem_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Problem_dealloc(ProblemObject *self);

extern PyObject *Problem_init(ProblemObject *self);
extern PyObject *Problem_string(ProblemObject *self);

extern PyObject *Problem_get_rule(ProblemObject *self);
extern PyObject *Problem_get_source(ProblemObject *self);
extern PyObject *Problem_get_target(ProblemObject *self);
extern PyObject *Problem_get_dep(ProblemObject *self);

extern PyObject *Problem_get_solutions(ProblemObject *self);

extern PyTypeObject ProblemType;

#endif
