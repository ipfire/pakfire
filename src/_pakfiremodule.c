
#include <Python.h>

#include "pool.h"
#include "problem.h"
#include "relation.h"
#include "repo.h"
#include "request.h"
#include "solvable.h"
#include "solver.h"
#include "step.h"
#include "transaction.h"

static PyMethodDef pakfireModuleMethods[] = {
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Pool_methods[] = {
	{"prepare", (PyCFunction)Pool_prepare, METH_NOARGS, NULL},
	{"size", (PyCFunction)Pool_size, METH_NOARGS, NULL},
	{"set_installed", (PyCFunction)Pool_set_installed, METH_VARARGS, NULL},
	{"providers", (PyCFunction)Pool_providers, METH_VARARGS, NULL},
	{"search", (PyCFunction)Pool_search, METH_VARARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Problem_methods[] = {
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Request_methods[] = {
	{"install_solvable", (PyCFunction)Request_install_solvable, METH_VARARGS, NULL},
	{"install_relation", (PyCFunction)Request_install_relation, METH_VARARGS, NULL},
	{"install_name", (PyCFunction)Request_install_name, METH_VARARGS, NULL},
	{"remove_solvable", (PyCFunction)Request_remove_solvable, METH_VARARGS, NULL},
	{"remove_relation", (PyCFunction)Request_remove_relation, METH_VARARGS, NULL},
	{"remove_name", (PyCFunction)Request_remove_name, METH_VARARGS, NULL},
	{"update_solvable", (PyCFunction)Request_update_solvable, METH_VARARGS, NULL},
	{"update_relation", (PyCFunction)Request_update_relation, METH_VARARGS, NULL},
	{"update_name", (PyCFunction)Request_update_name, METH_VARARGS, NULL},
	{"lock_solvable", (PyCFunction)Request_lock_solvable, METH_VARARGS, NULL},
	{"lock_relation", (PyCFunction)Request_lock_relation, METH_VARARGS, NULL},
	{"lock_name", (PyCFunction)Request_lock_name, METH_VARARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Relation_methods[] = {
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Repo_methods[] = {
	{"name", (PyCFunction)Repo_name, METH_NOARGS, NULL},
	{"size", (PyCFunction)Repo_size, METH_NOARGS, NULL},
	{"get_enabled", (PyCFunction)Repo_get_enabled, METH_NOARGS, NULL},
	{"set_enabled", (PyCFunction)Repo_set_enabled, METH_VARARGS, NULL},
	{"get_priority", (PyCFunction)Repo_get_priority, METH_NOARGS, NULL},
	{"set_priority", (PyCFunction)Repo_set_priority, METH_VARARGS, NULL},
	{"write", (PyCFunction)Repo_write, METH_VARARGS, NULL},
	{"read", (PyCFunction)Repo_read, METH_VARARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Solvable_methods[] = {
	{"get_name", (PyCFunction)Solvable_get_name, METH_NOARGS, NULL},
	{"get_evr", (PyCFunction)Solvable_get_evr, METH_NOARGS, NULL},
	{"get_arch", (PyCFunction)Solvable_get_arch, METH_NOARGS, NULL},
	{"get_vendor", (PyCFunction)Solvable_get_vendor, METH_NOARGS, NULL},
	{"set_vendor", (PyCFunction)Solvable_set_vendor, METH_VARARGS, NULL},
	{"get_repo_name", (PyCFunction)Solvable_get_repo_name, METH_NOARGS, NULL},
	{"get_uuid", (PyCFunction)Solvable_get_uuid, METH_NOARGS, NULL},
	{"set_uuid", (PyCFunction)Solvable_set_uuid, METH_VARARGS, NULL},
	{"get_hash1", (PyCFunction)Solvable_get_hash1, METH_NOARGS, NULL},
	{"set_hash1", (PyCFunction)Solvable_set_hash1, METH_VARARGS, NULL},
	{"get_summary", (PyCFunction)Solvable_get_summary, METH_NOARGS, NULL},
	{"set_summary", (PyCFunction)Solvable_set_summary, METH_VARARGS, NULL},
	{"get_description", (PyCFunction)Solvable_get_description, METH_NOARGS, NULL},
	{"set_description", (PyCFunction)Solvable_set_description, METH_VARARGS, NULL},
	{"get_groups", (PyCFunction)Solvable_get_groups, METH_NOARGS, NULL},
	{"set_groups", (PyCFunction)Solvable_set_groups, METH_VARARGS, NULL},
	{"get_url", (PyCFunction)Solvable_get_url, METH_NOARGS, NULL},
	{"set_url", (PyCFunction)Solvable_set_url, METH_VARARGS, NULL},
	{"get_filename", (PyCFunction)Solvable_get_filename, METH_NOARGS, NULL},
	{"set_filename", (PyCFunction)Solvable_set_filename, METH_VARARGS, NULL},
	{"get_license", (PyCFunction)Solvable_get_license, METH_NOARGS, NULL},
	{"set_license", (PyCFunction)Solvable_set_license, METH_VARARGS, NULL},
	{"get_buildhost", (PyCFunction)Solvable_get_buildhost, METH_NOARGS, NULL},
	{"set_buildhost", (PyCFunction)Solvable_set_buildhost, METH_VARARGS, NULL},
	{"get_maintainer", (PyCFunction)Solvable_get_maintainer, METH_NOARGS, NULL},
	{"set_maintainer", (PyCFunction)Solvable_set_maintainer, METH_VARARGS, NULL},
	{"get_downloadsize", (PyCFunction)Solvable_get_downloadsize, METH_NOARGS, NULL},
	{"set_downloadsize", (PyCFunction)Solvable_set_downloadsize, METH_VARARGS, NULL},
	{"get_installsize", (PyCFunction)Solvable_get_installsize, METH_NOARGS, NULL},
	{"set_installsize", (PyCFunction)Solvable_set_installsize, METH_VARARGS, NULL},
	{"get_buildtime", (PyCFunction)Solvable_get_buildtime, METH_NOARGS, NULL},
	{"set_buildtime", (PyCFunction)Solvable_set_buildtime, METH_VARARGS, NULL},
	{"add_provides", (PyCFunction)Solvable_add_provides, METH_VARARGS, NULL},
	{"get_provides", (PyCFunction)Solvable_get_provides, METH_NOARGS, NULL},
	{"add_requires", (PyCFunction)Solvable_add_requires, METH_VARARGS, NULL},
	{"get_requires", (PyCFunction)Solvable_get_requires, METH_NOARGS, NULL},
	{"add_obsoletes", (PyCFunction)Solvable_add_obsoletes, METH_VARARGS, NULL},
	{"get_obsoletes", (PyCFunction)Solvable_get_obsoletes, METH_NOARGS, NULL},
	{"add_conflicts", (PyCFunction)Solvable_add_conflicts, METH_VARARGS, NULL},
	{"get_conflicts", (PyCFunction)Solvable_get_conflicts, METH_NOARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Solver_methods[] = {
	{"solve", (PyCFunction)Solver_solve, METH_VARARGS, NULL},
	{"get_allow_downgrade", (PyCFunction)Solver_get_allow_downgrade, METH_NOARGS, NULL},
	{"set_allow_downgrade", (PyCFunction)Solver_set_allow_downgrade, METH_VARARGS, NULL},
	{"get_allow_archchange", (PyCFunction)Solver_get_allow_archchange, METH_NOARGS, NULL},
	{"set_allow_archchange", (PyCFunction)Solver_set_allow_archchange, METH_VARARGS, NULL},
	{"get_allow_vendorchange", (PyCFunction)Solver_get_allow_vendorchange, METH_NOARGS, NULL},
	{"set_allow_vendorchange", (PyCFunction)Solver_set_allow_vendorchange, METH_VARARGS, NULL},
	{"get_allow_uninstall", (PyCFunction)Solver_get_allow_uninstall, METH_NOARGS, NULL},
	{"set_allow_uninstall", (PyCFunction)Solver_set_allow_uninstall, METH_VARARGS, NULL},
	{"get_updatesystem", (PyCFunction)Solver_get_updatesystem, METH_NOARGS, NULL},
	{"set_updatesystem", (PyCFunction)Solver_set_updatesystem, METH_VARARGS, NULL},
	{"get_problems", (PyCFunction)Solver_get_problems, METH_VARARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Step_methods[] = {
	{"get_solvable", (PyCFunction)Step_get_solvable, METH_NOARGS, NULL},
	{"get_type", (PyCFunction)Step_get_type, METH_NOARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Transaction_methods[] = {
	{"steps", (PyCFunction)Transaction_steps, METH_NOARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

void init_pakfire(void) {
	PyObject *m, *d;

	m = Py_InitModule("_pakfire", pakfireModuleMethods);

	// Pool
	PoolType.tp_methods = Pool_methods;
	if (PyType_Ready(&PoolType) < 0)
		return;
	Py_INCREF(&PoolType);
	PyModule_AddObject(m, "Pool", (PyObject *)&PoolType);

	// Problem
	ProblemType.tp_methods = Problem_methods;
	if (PyType_Ready(&ProblemType) < 0)
		return;
	Py_INCREF(&ProblemType);
	PyModule_AddObject(m, "Problem", (PyObject *)&ProblemType);

	// Repo
	RepoType.tp_methods = Repo_methods;
	if (PyType_Ready(&RepoType) < 0)
		return;
	Py_INCREF(&RepoType);
	PyModule_AddObject(m, "Repo", (PyObject *)&RepoType);

	// Solvable
	SolvableType.tp_methods = Solvable_methods;
	if (PyType_Ready(&SolvableType) < 0)
		return;
	Py_INCREF(&SolvableType);
	PyModule_AddObject(m, "Solvable", (PyObject *)&SolvableType);

	// Relation
	RelationType.tp_methods = Relation_methods;
	if (PyType_Ready(&RelationType) < 0)
		return;
	Py_INCREF(&RelationType);
	PyModule_AddObject(m, "Relation", (PyObject *)&RelationType);

	// Request
	RequestType.tp_methods = Request_methods;
	if (PyType_Ready(&RequestType) < 0)
		return;
	Py_INCREF(&RequestType);
	PyModule_AddObject(m, "Request", (PyObject *)&RequestType);

	// Solver
	SolverType.tp_methods = Solver_methods;
	if (PyType_Ready(&SolverType) < 0)
		return;
	Py_INCREF(&SolverType);
	PyModule_AddObject(m, "Solver", (PyObject *)&SolverType);

	// Step
	StepType.tp_methods = Step_methods;
	if (PyType_Ready(&StepType) < 0)
		return;
	Py_INCREF(&StepType);
	PyModule_AddObject(m, "Step", (PyObject *)&StepType);

	// Transaction
	TransactionType.tp_methods = Transaction_methods;
	if (PyType_Ready(&TransactionType) < 0)
		return;
	Py_INCREF(&TransactionType);
	PyModule_AddObject(m, "Transaction", (PyObject *)&TransactionType);

	// Add constants
	d = PyModule_GetDict(m);

	// Add constants for relations
	PyDict_SetItemString(d, "REL_EQ", Py_BuildValue("i", REL_EQ));
	PyDict_SetItemString(d, "REL_LT", Py_BuildValue("i", REL_LT));
	PyDict_SetItemString(d, "REL_GT", Py_BuildValue("i", REL_GT));
	PyDict_SetItemString(d, "REL_LE", Py_BuildValue("i", REL_LT|REL_EQ));
	PyDict_SetItemString(d, "REL_GE", Py_BuildValue("i", REL_GT|REL_EQ));

	// Add constants for search
	PyDict_SetItemString(d, "SEARCH_STRING",		Py_BuildValue("i", SEARCH_STRING));
	PyDict_SetItemString(d, "SEARCH_STRINGSTART",	Py_BuildValue("i", SEARCH_STRINGSTART));
	PyDict_SetItemString(d, "SEARCH_STRINGEND",		Py_BuildValue("i", SEARCH_STRINGEND));
	PyDict_SetItemString(d, "SEARCH_SUBSTRING",		Py_BuildValue("i", SEARCH_SUBSTRING));
	PyDict_SetItemString(d, "SEARCH_GLOB",			Py_BuildValue("i", SEARCH_GLOB));
	PyDict_SetItemString(d, "SEARCH_REGEX",			Py_BuildValue("i", SEARCH_REGEX));
	PyDict_SetItemString(d, "SEARCH_FILES",			Py_BuildValue("i", SEARCH_FILES));
	PyDict_SetItemString(d, "SEARCH_CHECKSUMS",		Py_BuildValue("i", SEARCH_CHECKSUMS));
}
