
#ifndef PAKFIRE_TRANSACTION_H
#define PAKFIRE_TRANSACTION_H

#include <Python.h>

#include <satsolver/transaction.h>

// Sat Transaction object
typedef struct {
    PyObject_HEAD
    Pool *_pool;
    Transaction *_transaction;
} TransactionObject;

extern PyObject* Transaction_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
extern PyObject *Transaction_dealloc(TransactionObject *self);
extern PyObject *Transaction_steps(TransactionObject *self, PyObject *args);
extern PyObject *Transaction_get_installsizechange(TransactionObject *self);

extern PyTypeObject TransactionType;

#endif
