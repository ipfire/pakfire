
#include "pool.h"
#include "relation.h"
#include "request.h"
#include "solvable.h"

#include <satsolver/solver.h>

PyTypeObject RequestType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Request",
	tp_basicsize: sizeof(RequestObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Request_new,
	tp_dealloc: (destructor) Request_dealloc,
	tp_doc: "Sat Request objects",
};

PyObject* Request_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	RequestObject *self;
	PoolObject *pool;

	if (!PyArg_ParseTuple(args, "O", &pool)) {
		/* XXX raise exception */
	}

	self = (RequestObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_pool = pool->_pool;
		if (self->_pool == NULL) {
			Py_DECREF(self);
			return NULL;
		}

		queue_init(&self->_queue);
	}

	return (PyObject *)self;
}

PyObject *Request_dealloc(RequestObject *self) {
	self->ob_type->tp_free((PyObject *)self);
}

PyObject *Request_install_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		/* XXX raise exception */
	}

	queue_push(&self->_queue, SOLVER_INSTALL|SOLVER_SOLVABLE);
	queue_push(&self->_queue, solv->_id);

	Py_RETURN_NONE;
}

PyObject *Request_install_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
	}

	queue_push(&self->_queue, SOLVER_INSTALL|SOLVER_SOLVABLE_PROVIDES);
	queue_push(&self->_queue, rel->_id);

	Py_RETURN_NONE;
}

PyObject *Request_install_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	queue_push(&self->_queue, SOLVER_INSTALL|SOLVER_SOLVABLE_NAME);
	queue_push(&self->_queue, pool_str2id(self->_pool, name, 1));

	Py_RETURN_NONE;
}
