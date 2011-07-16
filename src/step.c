
#include "solvable.h"
#include "step.h"
#include "transaction.h"

PyTypeObject StepType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Step",
	tp_basicsize: sizeof(StepObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Step_new,
	tp_dealloc: (destructor) Step_dealloc,
	tp_doc: "Sat Step objects",
};

PyObject* Step_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	StepObject *self;
	TransactionObject *transaction;
	int num;

	if (!PyArg_ParseTuple(args, "Oi", &transaction, &num)) {
		/* XXX raise exception */
	}

	self = (StepObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_transaction = transaction->_transaction;

		if (num >= transaction->_transaction->steps.count) {
			Py_DECREF(self);
			return NULL;
		}

		self->_id = transaction->_transaction->steps.elements[num];
	}

	return (PyObject *)self;
}

PyObject *Step_dealloc(StepObject *self) {
	self->ob_type->tp_free((PyObject *)self);
}

PyObject *Step_get_solvable(StepObject *self, PyObject *args) {
	SolvableObject *solvable;

	solvable = PyObject_New(SolvableObject, &SolvableType);
	if (solvable == NULL)
		return NULL;

	solvable->_pool = self->_transaction->pool;
	solvable->_id = self->_id;

	return (PyObject *)solvable;
}

PyObject *Step_get_type(StepObject *self, PyObject *args) {
	const char *type = "unknown";

	int trans_type = transaction_type(self->_transaction, self->_id,
		SOLVER_TRANSACTION_SHOW_ACTIVE);

	switch(trans_type) {
		case SOLVER_TRANSACTION_IGNORE:
			type = "ignore";
			break;

		case SOLVER_TRANSACTION_ERASE:
			type = "erase";
			break;

		case SOLVER_TRANSACTION_REINSTALLED:
			type = "reinstalled";
			break;

		case SOLVER_TRANSACTION_DOWNGRADED:
			type = "downgraded";
			break;

		case SOLVER_TRANSACTION_CHANGED:
			type = "changed";
			break;

		case SOLVER_TRANSACTION_UPGRADED:
			type = "upgraded";
			break;

		case SOLVER_TRANSACTION_OBSOLETED:
			type = "obsoleted";
			break;

		case SOLVER_TRANSACTION_INSTALL:
			type = "install";
			break;

		case SOLVER_TRANSACTION_REINSTALL:
			type = "reinstall";
			break;

		case SOLVER_TRANSACTION_DOWNGRADE:
			type = "downgrade";
			break;

		case SOLVER_TRANSACTION_CHANGE:
			type = "change";
			break;

		case SOLVER_TRANSACTION_UPGRADE:
			type = "upgrade";
			break;

		case SOLVER_TRANSACTION_OBSOLETES:
			type = "obsoletes";
			break;

		case SOLVER_TRANSACTION_MULTIINSTALL:
			type = "multiinstall";
			break;

		case SOLVER_TRANSACTION_MULTIREINSTALL:
			type = "multireinstall";
			break;

		default:
			break;
	}

	return Py_BuildValue("s", type);
}
