
#include "pool.h"
#include "relation.h"

#define REL_NONE 0

PyTypeObject RelationType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Relation",
	tp_basicsize: sizeof(RelationObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Relation_new,
	tp_dealloc: (destructor) Relation_dealloc,
	tp_doc: "Sat Relation objects",
	tp_str: (reprfunc)Relation_string,
};

PyObject* Relation_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	RelationObject *self;
	PoolObject *pool;
	const char *name;
	const char *evr = NULL;
	int flags = 0;

	if (!PyArg_ParseTuple(args, "Os|si", &pool, &name, &evr, &flags)) {
		/* XXX raise exception */
		return NULL;
	}

	Id _name = pool_str2id(pool->_pool, name, 1);

	self = (RelationObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		if (flags == REL_NONE) {
			self->_id = _name;
		} else {
			Id _evr = pool_str2id(pool->_pool, evr, 1);
			self->_id = pool_rel2id(pool->_pool, _name, _evr, flags, 1);
		}

		self->_pool = pool->_pool;
	}

	return (PyObject *)self;
}

PyObject *Relation_dealloc(RelationObject *self) {
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Relation_string(RelationObject *self) {
	return Py_BuildValue("s", pool_dep2str(self->_pool, self->_id));
}
