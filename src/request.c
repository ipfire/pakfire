
#include "pool.h"
#include "relation.h"
#include "request.h"
#include "solvable.h"

#include <solv/solver.h>

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

	Py_RETURN_NONE;
}

void _Request_solvable(RequestObject *self, Id what, Id solvable) {
	queue_push(&self->_queue, what|SOLVER_SOLVABLE);
	queue_push(&self->_queue, solvable);
}

void _Request_relation(RequestObject *self, Id what, Id relation) {
	queue_push(&self->_queue, what|SOLVER_SOLVABLE_PROVIDES);
	queue_push(&self->_queue, relation);
}

void _Request_name(RequestObject *self, Id what, Id provides) {
	queue_push(&self->_queue, what|SOLVER_SOLVABLE_NAME);
	queue_push(&self->_queue, provides);
}

PyObject *Request_install_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		/* XXX raise exception */
	}

	_Request_solvable(self, SOLVER_INSTALL, solv->_id);

	Py_RETURN_NONE;
}

PyObject *Request_install_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
	}

	_Request_relation(self, SOLVER_INSTALL, rel->_id);

	Py_RETURN_NONE;
}

PyObject *Request_install_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_INSTALL, _name);

	Py_RETURN_NONE;
}

PyObject *Request_remove_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		/* XXX raise exception */
	}

	_Request_solvable(self, SOLVER_ERASE, solv->_id);

	Py_RETURN_NONE;
}

PyObject *Request_remove_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
	}

	_Request_relation(self, SOLVER_ERASE, rel->_id);

	Py_RETURN_NONE;
}

PyObject *Request_remove_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_ERASE, _name);

	Py_RETURN_NONE;
}

PyObject *Request_update_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		/* XXX raise exception */
	}

	_Request_solvable(self, SOLVER_UPDATE, solv->_id);

	Py_RETURN_NONE;
}

PyObject *Request_update_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
	}

	_Request_relation(self, SOLVER_UPDATE, rel->_id);

	Py_RETURN_NONE;
}

PyObject *Request_update_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_UPDATE, _name);

	Py_RETURN_NONE;
}

PyObject *Request_lock_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		/* XXX raise exception */
	}

	_Request_solvable(self, SOLVER_LOCK, solv->_id);

	Py_RETURN_NONE;
}

PyObject *Request_lock_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
	}

	_Request_relation(self, SOLVER_LOCK, rel->_id);

	Py_RETURN_NONE;
}

PyObject *Request_lock_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_LOCK, _name);

	Py_RETURN_NONE;
}

PyObject *Request_noobsoletes_solvable(RequestObject *self, PyObject *args) {
	SolvableObject *solv;

	if (!PyArg_ParseTuple(args, "O", &solv)) {
		/* XXX raise exception */
	}

	_Request_solvable(self, SOLVER_NOOBSOLETES, solv->_id);

	Py_RETURN_NONE;
}

PyObject *Request_noobsoletes_relation(RequestObject *self, PyObject *args) {
	RelationObject *rel;

	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
	}

	_Request_relation(self, SOLVER_NOOBSOLETES, rel->_id);

	Py_RETURN_NONE;
}

PyObject *Request_noobsoletes_name(RequestObject *self, PyObject *args) {
	const char *name;

	if (!PyArg_ParseTuple(args, "s", &name)) {
		/* XXX raise exception */
	}

	Id _name = pool_str2id(self->_pool, name, 1);
	_Request_name(self, SOLVER_NOOBSOLETES, _name);

	Py_RETURN_NONE;
}
