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
#include <sys/capability.h>

#include "config.h"

PyObject *
get_capabilities(PyObject *self, PyObject *args) {
	const char *filename;
	cap_t cap_d;
	char exception[STRING_SIZE];

        if (!PyArg_ParseTuple(args, "s", &filename)) {
                /* XXX raise exception */
                return NULL;
        }

	cap_d = cap_get_file(filename);
	if (cap_d == NULL) {
		if (errno == EOPNOTSUPP) {
			/* Return nothing, if the operation is not supported. */
			Py_RETURN_NONE;
		} else if (errno != ENODATA) {
			snprintf(exception, STRING_SIZE - 1, "Failed to get capabilities of file %s (%s).",
				filename, strerror(errno));
			PyErr_SetString(PyExc_RuntimeError, exception);
			return NULL;
		}
		Py_RETURN_NONE;
	}

	char *result = cap_to_text(cap_d, NULL);
	cap_free(cap_d);

	if (!result) {
		snprintf(exception, STRING_SIZE - 1, "Failed to get capabilities of human readable format at %s (%s).",
			filename, strerror(errno));
		PyErr_SetString(PyExc_RuntimeError, exception);
		return NULL;
	}

	// Remove leading two characters '= '.
	int i;
	for (i = 0; i < 2; i++) {
		result++;
	}

	PyObject * ret = Py_BuildValue("s", result);
	cap_free(result);

	return ret;
}

PyObject *
set_capabilities(PyObject *self, PyObject *args) {
	const char *filename;
	const char *input;
	char *exception = NULL;
	char buf[STRING_SIZE];
	cap_t cap_d;
	int ret;

	if (!PyArg_ParseTuple(args, "ss", &filename, &input)) {
		/* XXX raise exception */
		return NULL;
	}

	snprintf(buf, STRING_SIZE - 1, "= %s", input);
	cap_d = cap_from_text(buf);
	if (cap_d == NULL) {
		PyErr_SetString(PyExc_ValueError, "Could not read capability string.");
		return NULL;
	}

	ret = cap_set_file(filename, cap_d);
	cap_free(cap_d);

	if (ret != 0) {
		snprintf(exception, STRING_SIZE - 1, "Failed to set capabilities on file %s (%s).",
			filename, strerror(errno));
		PyErr_SetString(PyExc_RuntimeError, exception);
		return NULL;
	}

	return Py_BuildValue("i", ret);
}
