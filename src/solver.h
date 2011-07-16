
#ifndef PAKFIRE_SOLVER_H
#define PAKFIRE_SOLVER_H

#include <Python.h>

#include <satsolver/solver.h>

// Sat Solver object
typedef struct {
    PyObject_HEAD
    Solver *_solver;
} SolverObject;

extern PyObject* Solver_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Solver_dealloc(SolverObject *self);

extern PyObject *Solver_get_allow_downgrade(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_downgrade(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_allow_archchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_archchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_allow_vendorchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_vendorchange(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_allow_uninstall(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_allow_uninstall(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_updatesystem(SolverObject *self, PyObject *args);
extern PyObject *Solver_set_updatesystem(SolverObject *self, PyObject *args);

extern PyObject *Solver_solve(SolverObject *self, PyObject *args);
extern PyObject *Solver_get_problems(SolverObject *self, PyObject *args);

extern PyTypeObject SolverType;

#endif
