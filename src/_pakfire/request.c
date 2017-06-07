/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
#############################################################################*/

#include <Python.h>
#include <assert.h>

#include <pakfire/errno.h>
#include <pakfire/request.h>

#include "package.h"
#include "problem.h"
#include "relation.h"
#include "request.h"
#include "selector.h"
#include "transaction.h"

static PyObject* Request_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	RequestObject* self = (RequestObject *)type->tp_alloc(type, 0);
	if (self) {
		self->request = NULL;
		self->pool = NULL;
	}

	return (PyObject *)self;
}

static void Request_dealloc(RequestObject* self) {
	if (self->request)
		pakfire_request_free(self->request);

	Py_XDECREF(self->pool);
	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Request_init(RequestObject* self, PyObject* args, PyObject* kwds) {
	PyObject* pool;

	if (!PyArg_ParseTuple(args, "O!", &PoolType, &pool))
		return -1;

	self->pool = (PoolObject *)pool;
	Py_INCREF(self->pool);

	self->request = pakfire_request_create(self->pool->pool);

	return 0;
}

static int Request_args_parse(PyObject* args, PakfirePackage* pkg, PakfireRelation* relation, PakfireSelector* selector) {
	PyObject* obj = NULL;

	if (!PyArg_ParseTuple(args, "O", &obj))
		return 0;

	if (PyObject_TypeCheck(obj, &PackageType)) {
		PackageObject* pkg_obj = (PackageObject *)obj;
		*pkg = pkg_obj->package;

		return 1;
	}

	if (PyObject_TypeCheck(obj, &RelationType)) {
		RelationObject* relation_obj = (RelationObject *)obj;
		*relation = relation_obj->relation;

		return 1;
	}

	if (PyObject_TypeCheck(obj, &SelectorType)) {
		SelectorObject* selector_obj = (SelectorObject *)obj;
		*selector = selector_obj->selector;

		return 1;
	}

	PyErr_SetString(PyExc_ValueError, "Requires a Package, Relation or Selector object");
	return 0;
}

static PyObject* Request_operation_return(int ret) {
	if (!ret)
		Py_RETURN_NONE;

	switch (pakfire_get_errno()) {
		case PAKFIRE_E_SELECTOR:
			PyErr_SetString(PyExc_ValueError, "Ill-formed Selector");
			return NULL;

		default:
			PyErr_SetString(PyExc_RuntimeError, "Request operation failed");
			return NULL;
	}
}

static PyObject* Request_install(RequestObject* self, PyObject* args) {
	PakfirePackage pkg = NULL;
	PakfireRelation relation = NULL;
	PakfireSelector selector = NULL;

	if (!Request_args_parse(args, &pkg, &relation, &selector))
		return NULL;

	assert(pkg || relation || selector);

	int ret = 0;

	if (pkg)
		ret = pakfire_request_install(self->request, pkg);

	else if (relation)
		ret = pakfire_request_install_relation(self->request, relation);

	else if (selector)
		ret = pakfire_request_install_selector(self->request, selector);

	return Request_operation_return(ret);
}

static PyObject* Request_erase(RequestObject* self, PyObject* args) {
	PakfirePackage pkg = NULL;
	PakfireRelation relation = NULL;
	PakfireSelector selector = NULL;

	if (!Request_args_parse(args, &pkg, &relation, &selector))
		return NULL;

	assert(pkg || relation || selector);

	int ret = 0;

	if (pkg)
		ret = pakfire_request_erase(self->request, pkg, 0);

	else if (selector)
		ret = pakfire_request_erase_selector(self->request, selector, 0);

	return Request_operation_return(ret);
}

static PyObject* Request_upgrade(RequestObject* self, PyObject* args) {
	PakfirePackage pkg = NULL;
	PakfireRelation relation = NULL;
	PakfireSelector selector = NULL;

	if (!Request_args_parse(args, &pkg, &relation, &selector))
		return NULL;

	assert(pkg || relation || selector);

	int ret = 0;

	if (pkg)
		ret = pakfire_request_upgrade(self->request, pkg);

	else if (relation)
		ret = pakfire_request_upgrade_relation(self->request, relation);

	else if (selector)
		ret = pakfire_request_upgrade_selector(self->request, selector);

	return Request_operation_return(ret);
}

static PyObject* Request_upgrade_all(RequestObject* self) {
	int ret = pakfire_request_upgrade_all(self->request);

	return Request_operation_return(ret);
}

static PyObject* Request_distupgrade(RequestObject* self) {
	int ret = pakfire_request_distupgrade(self->request);

	return Request_operation_return(ret);
}

static PyObject* Request_solve(RequestObject* self) {
	int ret = pakfire_request_solve(self->request, 0);

	if (ret)
		Py_RETURN_NONE;

	// Allocate the transaction and return it
	PakfireTransaction transaction = pakfire_request_get_transaction(self->request);
	assert(transaction);

	return new_transaction(self, transaction);
}

static PyObject* Request_get_pool(RequestObject* self) {
	PoolObject* pool = self->pool;
	Py_INCREF(pool);

	return (PyObject *)pool;
}

static PyObject* Request_get_problems(RequestObject* self) {
	PyObject* list = PyList_New(0);

	PakfireProblem problem = pakfire_request_get_problems(self->request);
	while (problem) {
		PyObject* p = new_problem(problem);
		PyList_Append(list, p);

		Py_DECREF(p);

		// Move on to next problem
		problem = pakfire_problem_next(problem);
	}

	return list;
}

static struct PyMethodDef Request_methods[] = {
	{
		"install",
		(PyCFunction)Request_install,
		METH_VARARGS,
		NULL
	},
	{
		"erase",
		(PyCFunction)Request_erase,
		METH_VARARGS,
		NULL
	},
	{
		"upgrade",
		(PyCFunction)Request_upgrade,
		METH_VARARGS,
		NULL
	},
	{
		"upgrade_all",
		(PyCFunction)Request_upgrade_all,
		METH_NOARGS,
		NULL
	},
	{
		"distupgrade",
		(PyCFunction)Request_distupgrade,
		METH_NOARGS,
		NULL
	},
	{
		"solve",
		(PyCFunction)Request_solve,
		METH_NOARGS,
		NULL
	},
	{ NULL }
};

static struct PyGetSetDef Request_getsetters[] = {
	{
		"problems",
		(getter)Request_get_problems,
		NULL,
		NULL,
		NULL
	},
	{
		"pool",
		(getter)Request_get_pool,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

PyTypeObject RequestType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Request",
	tp_basicsize:       sizeof(RequestObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Request_new,
	tp_dealloc:         (destructor)Request_dealloc,
	tp_init:            (initproc)Request_init,
	tp_doc:             "Request object",
	tp_methods:         Request_methods,
	tp_getset:          Request_getsetters,
};
