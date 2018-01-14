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

#include <errno.h>
#include <sched.h>
#include <sys/personality.h>
#include <time.h>
#include <unistd.h>

#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/types.h>

#include "constants.h"
#include "package.h"
#include "util.h"

PyObject *_personality(PyObject *self, PyObject *args) {
	unsigned long persona;
	int ret = 0;

	if (!PyArg_ParseTuple(args, "l", &persona)) {
		/* XXX raise exception */
		return NULL;
	}

	/* Change personality here. */
	ret = personality(persona);

	if (ret < 0) {
		PyErr_SetString(PyExc_RuntimeError, "Could not set personality.");
		return NULL;
	}

	return Py_BuildValue("i", ret);
}

PyObject *_sync(PyObject *self, PyObject *args) {
	/* Just sync everything to disks. */
	sync();

	Py_RETURN_NONE;
}

PyObject *_unshare(PyObject *self, PyObject *args) {
	int flags = 0;

	if (!PyArg_ParseTuple(args, "i", &flags)) {
		return NULL;
	}

	int ret = unshare(flags);
	if (ret < 0) {
		return PyErr_SetFromErrno(PyExc_RuntimeError);
	}

	return Py_BuildValue("i", ret);
}

PyObject *version_compare(PyObject *self, PyObject *args) {
	Pool *pool;
	const char *evr1, *evr2;

	if (!PyArg_ParseTuple(args, "Oss", &pool, &evr1, &evr2)) {
		/* XXX raise exception */
		return NULL;
	}

	int ret = pool_evrcmp_str(pool, evr1, evr2, EVRCMP_COMPARE);

	return Py_BuildValue("i", ret);
}

static unsigned long fibonnacci(const clock_t* deadline) {
	clock_t now = clock();

	unsigned long f1 = 1;
	unsigned long f2 = 1;

	// Count iterations
	unsigned long counter = 0;

	while (now < *deadline) {
		unsigned long next = f1 + f2;
		f1 = f2;
		f2 = next;

		now = clock();
		counter++;
	}

	return counter;
}

PyObject* performance_index(PyObject* self, PyObject* args) {
	int seconds = 1;

	if (!PyArg_ParseTuple(args, "|i", &seconds)) {
		return NULL;
	}

	if (seconds == 0) {
		PyErr_SetString(PyExc_ValueError, "Runtime must be one second or longer");
		return NULL;
	}

	// Determine the number of online processors
	int processors = sysconf(_SC_NPROCESSORS_ONLN);

	// Determine deadline
	clock_t deadline = clock();
	deadline += CLOCKS_PER_SEC * seconds;

	// Run Fibonnacci until deadline
	unsigned long iterations = fibonnacci(&deadline);

	// Times the result by the number of processors
	iterations *= processors;

	// Normalise to a second
	iterations /= seconds;

	return PyLong_FromUnsignedLong(iterations);
}

PyObject* PyList_FromPackageList(PoolObject* pool, PakfirePackageList packagelist) {
	PyObject* list = PyList_New(0);

	int count = pakfire_packagelist_count(packagelist);
	for (int i = 0; i < count; i++) {
		PakfirePackage package = pakfire_packagelist_get(packagelist, i);

		PyObject* item = new_package(pool, pakfire_package_id(package));
		PyList_Append(list, item);

		pakfire_package_unref(package);
		Py_DECREF(item);
	}

	return list;
}
