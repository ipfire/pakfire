
#ifndef PAKFIRE_SOLVABLE_H
#define PAKFIRE_SOLVABLE_H

#include <Python.h>

#include <satsolver/solvable.h>

// Sat Solvable object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Id _id;
} SolvableObject;

extern PyObject* Solvable_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Solvable_dealloc(SolvableObject *self);
extern PyObject *Solvable_get_name(SolvableObject *self);
extern PyObject *Solvable_get_evr(SolvableObject *self);
extern PyObject *Solvable_get_arch(SolvableObject *self);

extern PyObject *Solvable_get_vendor(SolvableObject *self);
extern PyObject *Solvable_set_vendor(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_repo_name(SolvableObject *self);

extern PyObject *Solvable_get_uuid(SolvableObject *self);
extern PyObject *Solvable_set_uuid(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_hash1(SolvableObject *self);
extern PyObject *Solvable_set_hash1(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_summary(SolvableObject *self);
extern PyObject *Solvable_set_summary(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_description(SolvableObject *self);
extern PyObject *Solvable_set_description(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_groups(SolvableObject *self);
extern PyObject *Solvable_set_groups(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_url(SolvableObject *self);
extern PyObject *Solvable_set_url(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_filename(SolvableObject *self);
extern PyObject *Solvable_set_filename(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_license(SolvableObject *self);
extern PyObject *Solvable_set_license(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_buildhost(SolvableObject *self);
extern PyObject *Solvable_set_buildhost(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_maintainer(SolvableObject *self);
extern PyObject *Solvable_set_maintainer(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_downloadsize(SolvableObject *self);
extern PyObject *Solvable_set_downloadsize(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_installsize(SolvableObject *self);
extern PyObject *Solvable_set_installsize(SolvableObject *self, PyObject *args);

extern PyObject *Solvable_get_buildtime(SolvableObject *self);
extern PyObject *Solvable_set_buildtime(SolvableObject *self, PyObject *args);

// internal use only
extern PyObject *_Solvable_get_dependencies(Solvable *solv, Offset deps);

extern PyObject *Solvable_add_provides(SolvableObject *self, PyObject *args);
extern PyObject *Solvable_get_provides(SolvableObject *self);

extern PyObject *Solvable_add_requires(SolvableObject *self, PyObject *args);
extern PyObject *Solvable_get_requires(SolvableObject *self);

extern PyObject *Solvable_add_obsoletes(SolvableObject *self, PyObject *args);
extern PyObject *Solvable_get_obsoletes(SolvableObject *self);

extern PyObject *Solvable_add_conflicts(SolvableObject *self, PyObject *args);
extern PyObject *Solvable_get_conflicts(SolvableObject *self);

extern PyTypeObject SolvableType;

#endif
