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

#include <libintl.h>
#include <locale.h>
#include <sched.h>
#include <sys/personality.h>

#include "archive.h"
#include "capabilities.h"
#include "constants.h"
#include "package.h"
#include "pool.h"
#include "problem.h"
#include "relation.h"
#include "repo.h"
#include "request.h"
#include "solution.h"
#include "solvable.h"
#include "solver.h"
#include "step.h"
#include "transaction.h"
#include "util.h"

static PyMethodDef pakfireModuleMethods[] = {
	{"performance_index", (PyCFunction)performance_index, METH_VARARGS, NULL},
	{"version_compare", (PyCFunction)version_compare, METH_VARARGS, NULL},
	{"get_capabilities", (PyCFunction)get_capabilities, METH_VARARGS, NULL},
	{"set_capabilities", (PyCFunction)set_capabilities, METH_VARARGS, NULL},
	{"personality", (PyCFunction)_personality, METH_VARARGS, NULL},
	{"sync", (PyCFunction)_sync, METH_NOARGS, NULL},
	{"unshare", (PyCFunction)_unshare, METH_VARARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Problem_methods[] = {
	{"get_rule", (PyCFunction)Problem_get_rule, METH_NOARGS, NULL},
	{"get_source", (PyCFunction)Problem_get_source, METH_NOARGS, NULL},
	{"get_target", (PyCFunction)Problem_get_target, METH_NOARGS, NULL},
	{"get_dep", (PyCFunction)Problem_get_dep, METH_NOARGS, NULL},
	{"get_solutions", (PyCFunction)Problem_get_solutions, METH_NOARGS, NULL},
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
	{"noobsoletes_solvable", (PyCFunction)Request_noobsoletes_solvable, METH_VARARGS, NULL},
	{"noobsoletes_relation", (PyCFunction)Request_noobsoletes_relation, METH_VARARGS, NULL},
	{"noobsoletes_name", (PyCFunction)Request_noobsoletes_name, METH_VARARGS, NULL},
	{"updateall", (PyCFunction)Request_updateall, METH_NOARGS, NULL},
	{"distupgrade", (PyCFunction)Request_distupgrade, METH_NOARGS, NULL},
	{"verify", (PyCFunction)Request_verify, METH_NOARGS, NULL},
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
	{"add_recommends", (PyCFunction)Solvable_add_recommends, METH_VARARGS, NULL},
	{"get_recommends", (PyCFunction)Solvable_get_recommends, METH_NOARGS, NULL},
	{"add_suggests", (PyCFunction)Solvable_add_suggests, METH_VARARGS, NULL},
	{"get_suggests", (PyCFunction)Solvable_get_suggests, METH_NOARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Solution_methods[] = {
	{ NULL, NULL, 0, NULL }
};

static PyMethodDef Solver_methods[] = {
	{"solve", (PyCFunction)Solver_solve, METH_VARARGS, NULL},
	{"get_flag", (PyCFunction)Solver_get_flag, METH_VARARGS, NULL},
	{"set_flag", (PyCFunction)Solver_set_flag, METH_VARARGS, NULL},
	{"get_allow_archchange", (PyCFunction)Solver_get_allow_archchange, METH_NOARGS, NULL},
	{"set_allow_archchange", (PyCFunction)Solver_set_allow_archchange, METH_VARARGS, NULL},
	{"get_allow_vendorchange", (PyCFunction)Solver_get_allow_vendorchange, METH_NOARGS, NULL},
	{"set_allow_vendorchange", (PyCFunction)Solver_set_allow_vendorchange, METH_VARARGS, NULL},
	{"get_allow_uninstall", (PyCFunction)Solver_get_allow_uninstall, METH_NOARGS, NULL},
	{"set_allow_uninstall", (PyCFunction)Solver_set_allow_uninstall, METH_VARARGS, NULL},
	{"get_updatesystem", (PyCFunction)Solver_get_updatesystem, METH_NOARGS, NULL},
	{"set_updatesystem", (PyCFunction)Solver_set_updatesystem, METH_VARARGS, NULL},
	{"get_do_split_provides", (PyCFunction)Solver_get_do_split_provides, METH_NOARGS, NULL},
	{"set_do_split_provides", (PyCFunction)Solver_set_do_split_provides, METH_VARARGS, NULL},
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
	{"get_installsizechange", (PyCFunction)Transaction_get_installsizechange, METH_NOARGS, NULL},
	{ NULL, NULL, 0, NULL }
};

static struct PyModuleDef moduledef = {
	.m_base = PyModuleDef_HEAD_INIT,
	.m_name = "_pakfire",
	.m_size = -1,
	.m_methods = pakfireModuleMethods,
};

PyMODINIT_FUNC PyInit__pakfire(void) {
	/* Initialize locale */
	setlocale(LC_ALL, "");
	bindtextdomain(PACKAGE_TARNAME, "/usr/share/locale");
	textdomain(PACKAGE_TARNAME);

	// Create the module
	PyObject* module = PyModule_Create(&moduledef);
	if (!module)
		return NULL;

	// Archive
	if (PyType_Ready(&ArchiveType) < 0)
		return NULL;

	Py_INCREF(&ArchiveType);
	PyModule_AddObject(module, "Archive", (PyObject *)&ArchiveType);

	// Package
	if (PyType_Ready(&PackageType) < 0)
		return NULL;

	Py_INCREF(&PackageType);
	PyModule_AddObject(module, "Package", (PyObject *)&PackageType);

	// Pool
	if (PyType_Ready(&PoolType) < 0)
		return NULL;
	Py_INCREF(&PoolType);
	PyModule_AddObject(module, "Pool", (PyObject *)&PoolType);

	// Problem
	ProblemType.tp_methods = Problem_methods;
	if (PyType_Ready(&ProblemType) < 0)
		return NULL;
	Py_INCREF(&ProblemType);
	PyModule_AddObject(module, "Problem", (PyObject *)&ProblemType);

	// Repo
	if (PyType_Ready(&RepoType) < 0)
		return NULL;

	Py_INCREF(&RepoType);
	PyModule_AddObject(module, "Repo", (PyObject *)&RepoType);

	// Solvable
	SolvableType.tp_methods = Solvable_methods;
	if (PyType_Ready(&SolvableType) < 0)
		return NULL;
	Py_INCREF(&SolvableType);
	PyModule_AddObject(module, "Solvable", (PyObject *)&SolvableType);

	// Relation
	if (PyType_Ready(&RelationType) < 0)
		return NULL;

	Py_INCREF(&RelationType);
	PyModule_AddObject(module, "Relation", (PyObject *)&RelationType);

	// Request
	RequestType.tp_methods = Request_methods;
	if (PyType_Ready(&RequestType) < 0)
		return NULL;
	Py_INCREF(&RequestType);
	PyModule_AddObject(module, "Request", (PyObject *)&RequestType);

	// Solution
	SolutionType.tp_methods = Solution_methods;
	if (PyType_Ready(&SolutionType) < 0)
		return NULL;
	Py_INCREF(&SolutionType);
	PyModule_AddObject(module, "Solution", (PyObject *)&SolutionType);

	// Solver
	SolverType.tp_methods = Solver_methods;
	if (PyType_Ready(&SolverType) < 0)
		return NULL;
	Py_INCREF(&SolverType);
	PyModule_AddObject(module, "Solver", (PyObject *)&SolverType);

	// Step
	StepType.tp_methods = Step_methods;
	if (PyType_Ready(&StepType) < 0)
		return NULL;
	Py_INCREF(&StepType);
	PyModule_AddObject(module, "Step", (PyObject *)&StepType);

	// Transaction
	TransactionType.tp_methods = Transaction_methods;
	if (PyType_Ready(&TransactionType) < 0)
		return NULL;
	Py_INCREF(&TransactionType);
	PyModule_AddObject(module, "Transaction", (PyObject *)&TransactionType);

	// Add constants
	PyObject* d = PyModule_GetDict(module);

	// Personalities
	PyDict_SetItemString(d, "PERSONALITY_LINUX",   Py_BuildValue("i", PER_LINUX));
	PyDict_SetItemString(d, "PERSONALITY_LINUX32", Py_BuildValue("i", PER_LINUX32));

	// Namespace stuff
	PyDict_SetItemString(d, "SCHED_CLONE_NEWIPC", Py_BuildValue("i", CLONE_NEWIPC));
	PyDict_SetItemString(d, "SCHED_CLONE_NEWPID", Py_BuildValue("i", CLONE_NEWPID));
	PyDict_SetItemString(d, "SCHED_CLONE_NEWNET", Py_BuildValue("i", CLONE_NEWNET));
	PyDict_SetItemString(d, "SCHED_CLONE_NEWNS",  Py_BuildValue("i", CLONE_NEWNS));
	PyDict_SetItemString(d, "SCHED_CLONE_NEWUTS", Py_BuildValue("i", CLONE_NEWUTS));

	// Add constants for relations
	PyDict_SetItemString(d, "REL_EQ", Py_BuildValue("i", REL_EQ));
	PyDict_SetItemString(d, "REL_LT", Py_BuildValue("i", REL_LT));
	PyDict_SetItemString(d, "REL_GT", Py_BuildValue("i", REL_GT));
	PyDict_SetItemString(d, "REL_LE", Py_BuildValue("i", REL_LT|REL_EQ));
	PyDict_SetItemString(d, "REL_GE", Py_BuildValue("i", REL_GT|REL_EQ));

	// Add constants for search
	PyDict_SetItemString(d, "SEARCH_STRING",	Py_BuildValue("i", SEARCH_STRING));
	PyDict_SetItemString(d, "SEARCH_STRINGSTART",	Py_BuildValue("i", SEARCH_STRINGSTART));
	PyDict_SetItemString(d, "SEARCH_STRINGEND",	Py_BuildValue("i", SEARCH_STRINGEND));
	PyDict_SetItemString(d, "SEARCH_SUBSTRING",	Py_BuildValue("i", SEARCH_SUBSTRING));
	PyDict_SetItemString(d, "SEARCH_GLOB",		Py_BuildValue("i", SEARCH_GLOB));
	PyDict_SetItemString(d, "SEARCH_REGEX",		Py_BuildValue("i", SEARCH_REGEX));
	PyDict_SetItemString(d, "SEARCH_FILES",		Py_BuildValue("i", SEARCH_FILES));
	PyDict_SetItemString(d, "SEARCH_CHECKSUMS",	Py_BuildValue("i", SEARCH_CHECKSUMS));

	// Add constants for rules
	PyDict_SetItemString(d, "SOLVER_RULE_DISTUPGRADE",			Py_BuildValue("i", SOLVER_RULE_DISTUPGRADE));
	PyDict_SetItemString(d, "SOLVER_RULE_INFARCH",				Py_BuildValue("i", SOLVER_RULE_INFARCH));
	PyDict_SetItemString(d, "SOLVER_RULE_UPDATE",				Py_BuildValue("i", SOLVER_RULE_UPDATE));
	PyDict_SetItemString(d, "SOLVER_RULE_JOB",				Py_BuildValue("i", SOLVER_RULE_JOB));
	PyDict_SetItemString(d, "SOLVER_RULE_JOB_NOTHING_PROVIDES_DEP",		Py_BuildValue("i", SOLVER_RULE_JOB_NOTHING_PROVIDES_DEP));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM",				Py_BuildValue("i", SOLVER_RULE_RPM));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_NOT_INSTALLABLE",		Py_BuildValue("i", SOLVER_RULE_RPM_NOT_INSTALLABLE));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_NOTHING_PROVIDES_DEP",		Py_BuildValue("i", SOLVER_RULE_RPM_NOTHING_PROVIDES_DEP));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_SAME_NAME",			Py_BuildValue("i", SOLVER_RULE_RPM_SAME_NAME));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_PACKAGE_CONFLICT",		Py_BuildValue("i", SOLVER_RULE_RPM_PACKAGE_CONFLICT));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_PACKAGE_OBSOLETES",		Py_BuildValue("i", SOLVER_RULE_RPM_PACKAGE_OBSOLETES));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_INSTALLEDPKG_OBSOLETES",	Py_BuildValue("i", SOLVER_RULE_RPM_INSTALLEDPKG_OBSOLETES));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_IMPLICIT_OBSOLETES",		Py_BuildValue("i", SOLVER_RULE_RPM_IMPLICIT_OBSOLETES));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_PACKAGE_REQUIRES",		Py_BuildValue("i", SOLVER_RULE_RPM_PACKAGE_REQUIRES));
	PyDict_SetItemString(d, "SOLVER_RULE_RPM_SELF_CONFLICT",		Py_BuildValue("i", SOLVER_RULE_RPM_SELF_CONFLICT));
	PyDict_SetItemString(d, "SOLVER_RULE_UNKNOWN",				Py_BuildValue("i", SOLVER_RULE_UNKNOWN));
	PyDict_SetItemString(d, "SOLVER_RULE_FEATURE",				Py_BuildValue("i", SOLVER_RULE_FEATURE));
	PyDict_SetItemString(d, "SOLVER_RULE_LEARNT",				Py_BuildValue("i", SOLVER_RULE_LEARNT));
	PyDict_SetItemString(d, "SOLVER_RULE_CHOICE",				Py_BuildValue("i", SOLVER_RULE_CHOICE));

	/* Solver flags */
	PyDict_SetItemString(d, "SOLVER_FLAG_ALLOW_DOWNGRADE", Py_BuildValue("i", SOLVER_FLAG_ALLOW_DOWNGRADE));
	PyDict_SetItemString(d, "SOLVER_FLAG_ALLOW_ARCHCHANGE", Py_BuildValue("i", SOLVER_FLAG_ALLOW_ARCHCHANGE));
	PyDict_SetItemString(d, "SOLVER_FLAG_ALLOW_VENDORCHANGE", Py_BuildValue("i", SOLVER_FLAG_ALLOW_VENDORCHANGE));
	PyDict_SetItemString(d, "SOLVER_FLAG_ALLOW_UNINSTALL", Py_BuildValue("i", SOLVER_FLAG_ALLOW_UNINSTALL));
	PyDict_SetItemString(d, "SOLVER_FLAG_NO_UPDATEPROVIDE", Py_BuildValue("i", SOLVER_FLAG_NO_UPDATEPROVIDE));
	PyDict_SetItemString(d, "SOLVER_FLAG_SPLITPROVIDES", Py_BuildValue("i", SOLVER_FLAG_SPLITPROVIDES));
	PyDict_SetItemString(d, "SOLVER_FLAG_IGNORE_RECOMMENDED", Py_BuildValue("i", SOLVER_FLAG_IGNORE_RECOMMENDED));

	return module;
}
