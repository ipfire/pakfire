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

#include "errors.h"
#include "package.h"
#include "pakfire.h"
#include "problem.h"
#include "relation.h"
#include "request.h"
#include "selector.h"
#include "transaction.h"

static PyObject* Request_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	RequestObject* self = (RequestObject *)type->tp_alloc(type, 0);
	if (self) {
		self->request = NULL;
		self->pakfire = NULL;
	}

	return (PyObject *)self;
}

static void Request_dealloc(RequestObject* self) {
	if (self->request)
		pakfire_request_unref(self->request);

	Py_XDECREF(self->pakfire);
	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Request_init(RequestObject* self, PyObject* args, PyObject* kwds) {
	PakfireObject* pakfire;

	if (!PyArg_ParseTuple(args, "O!", &PakfireType, &pakfire))
		return -1;

	self->pakfire = pakfire;
	Py_INCREF(self->pakfire);

	self->request = pakfire_request_create(self->pakfire->pakfire);

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

static PyObject* Request_verify(RequestObject* self) {
	int ret = pakfire_request_verify(self->request);

	return Request_operation_return(ret);
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

static PyObject* Request_solve(RequestObject* self, PyObject* args, PyObject *kwds) {
	char* kwlist[] = {"allow_archchange", "allow_downgrade", "allow_uninstall",
		"allow_vendorchange", "without_recommends", NULL};

	int allow_archchange = 0;
	int allow_downgrade = 0;
	int allow_uninstall = 0;
	int allow_vendorchange = 0;
	int without_recommends = 0;

	if (!PyArg_ParseTupleAndKeywords(args, kwds, "|ppppp", kwlist,
			&allow_archchange, &allow_downgrade, &allow_uninstall,
			&allow_vendorchange, &without_recommends))
		return NULL;

	int flags = 0;
	if (allow_archchange)
		flags |= PAKFIRE_SOLVER_ALLOW_ARCHCHANGE;

	if (allow_downgrade)
		flags |= PAKFIRE_SOLVER_ALLOW_DOWNGRADE;

	if (allow_uninstall)
		flags |= PAKFIRE_SOLVER_ALLOW_UNINSTALL;

	if (allow_vendorchange)
		flags |= PAKFIRE_SOLVER_ALLOW_VENDORCHANGE;

	if (without_recommends)
		flags |= PAKFIRE_SOLVER_WITHOUT_RECOMMENDS;

	int ret = pakfire_request_solve(self->request, flags);

	// Raise a DependencyError with all problems
	// if the request could not be solved
	if (ret) {
		PyObject* problems = Request_get_problems(self);
		PyErr_SetObject(PyExc_DependencyError, problems);

		Py_DECREF(problems);
		return NULL;
	}

	// Allocate the transaction and return it
	PakfireTransaction transaction = pakfire_request_get_transaction(self->request);
	assert(transaction);

	return new_transaction(self, transaction);
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
		"verify",
		(PyCFunction)Request_verify,
		METH_NOARGS,
		NULL
	},
	{
		"solve",
		(PyCFunction)Request_solve,
		METH_VARARGS|METH_KEYWORDS,
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
