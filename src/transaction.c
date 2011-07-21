
#include "solver.h"
#include "step.h"
#include "transaction.h"

PyTypeObject TransactionType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Transaction",
	tp_basicsize: sizeof(TransactionObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Transaction_new,
	tp_dealloc: (destructor) Transaction_dealloc,
	tp_doc: "Sat Transaction objects",
};

PyObject* Transaction_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	TransactionObject *self;
	SolverObject *solver;

	if (!PyArg_ParseTuple(args, "O", &solver)) {
		/* XXX raise exception */
	}

	self = (TransactionObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_pool = solver->_solver->pool;
		if (self->_pool == NULL) {
			Py_DECREF(self);
			return NULL;
		}

		/* When the solver is freed we still need the transaction. For that,
		   we copy it to be independent. */
		self->_transaction = malloc(sizeof(Transaction));
		memcpy(self->_transaction, &solver->_solver->trans, sizeof(Transaction));

		// order the transaction right from the start.
		transaction_order(self->_transaction, 0);
	}

	return (PyObject *)self;
}

PyObject *Transaction_dealloc(TransactionObject *self) {
	/* XXX need to free self->_transaction */
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Transaction_steps(TransactionObject *self, PyObject *args) {
	PyObject *list = PyList_New(0);

	StepObject *step;
	int i = 0;
	for(; i < self->_transaction->steps.count; i++) {
		step = PyObject_New(StepObject, &StepType);
		step->_transaction = self->_transaction;
		step->_id = self->_transaction->steps.elements[i];

		PyList_Append(list, (PyObject *)step);
	}

	Py_INCREF(list); // XXX do we need this here?
	return list;
}
