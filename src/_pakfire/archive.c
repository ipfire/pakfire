/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2014 Pakfire development team                                 #
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

#include <pakfire/archive.h>
#include <pakfire/package.h>
#include <pakfire/repo.h>
#include <pakfire/util.h>

#include "archive.h"
#include "errors.h"
#include "package.h"

static PyObject* Archive_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	ArchiveObject* self = (ArchiveObject *)type->tp_alloc(type, 0);
	if (self) {
		self->archive = NULL;
	}

	return (PyObject *)self;
}

static void Archive_dealloc(ArchiveObject* self) {
	pakfire_archive_unref(self->archive);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Archive_init(ArchiveObject* self, PyObject* args, PyObject* kwds) {
	PakfireObject* pakfire = NULL;
	const char* filename = NULL;

	if (!PyArg_ParseTuple(args, "O!s", &PakfireType, &pakfire, &filename))
		return -1;

	self->archive = pakfire_archive_open(pakfire->pakfire, filename);
	if (!self->archive) {
		PyErr_SetFromErrno(PyExc_OSError);
		return -1;
	}

	return 0;
}

static PyObject* Archive_get_format(ArchiveObject* self) {
	unsigned int format = pakfire_archive_get_format(self->archive);

	return PyLong_FromUnsignedLong(format);
}

static PyObject* Archive_read(ArchiveObject* self, PyObject* args, PyObject* kwds) {
	char* kwlist[] = {"filename", "payload", NULL};

	const char* filename = NULL;
	int payload = 0;

	if (!PyArg_ParseTupleAndKeywords(args, kwds, "s|i", kwlist, &filename, &payload))
		return NULL;

	int flags = 0;
	if (payload)
		flags |= PAKFIRE_ARCHIVE_USE_PAYLOAD;

	if (!filename)
		Py_RETURN_NONE;

	void* data = NULL;
	size_t data_size = 0;

	int ret = pakfire_archive_read(self->archive, filename, &data, &data_size, flags);
	if (ret) {
		pakfire_free(data);

		Py_RETURN_NONE;
	}

	// XXX This is not ideal since PyBytes_FromStringAndSize creates a
	// copy of data.
	PyObject* bytes = PyBytes_FromStringAndSize(data, data_size);
	pakfire_free(data);

	return bytes;
}

static PyObject* Archive_verify(ArchiveObject* self) {
	pakfire_archive_verify_status_t status = pakfire_archive_verify(self->archive);

	// Return True if everything is fine
	if (status == PAKFIRE_ARCHIVE_VERIFY_OK || status == PAKFIRE_ARCHIVE_VERIFY_KEY_EXPIRED)
		Py_RETURN_TRUE;

	// Raise an exception if not okay
	PyErr_SetString(PyExc_BadSignatureError, pakfire_archive_verify_strerror(status));

	return NULL;
}

static PyObject* Archive_get_signatures(ArchiveObject* self) {
	PyObject* list = PyList_New(0);

	PakfireArchiveSignature* head = pakfire_archive_get_signatures(self->archive);

	PakfireArchiveSignature* signatures = head;
	while (signatures && *signatures) {
		PakfireArchiveSignature signature = *signatures++;

		PyObject* object = new_archive_signature(self, signature);
		PyList_Append(list, object);

		Py_DECREF(object);
	}

	return list;
}

static PyObject* Archive_extract(ArchiveObject* self, PyObject* args) {
	const char* target = NULL;

	if (!PyArg_ParseTuple(args, "|z", &target))
		return NULL;

	// Make extraction path
	char* prefix = pakfire_archive_extraction_path(self->archive, target);

	// Extract payload
	int r = pakfire_archive_extract(self->archive, prefix, PAKFIRE_ARCHIVE_USE_PAYLOAD);
	pakfire_free(prefix);

	// Throw an exception on error
	if (r) {
		PyErr_SetFromErrno(PyExc_OSError);
		return NULL;
	}

	Py_RETURN_NONE;
}

static PyObject* Archive_get_package(ArchiveObject* self) {
	Pakfire pakfire = pakfire_archive_get_pakfire(self->archive);

	PakfireRepo repo = pakfire_repo_create(pakfire, "dummy");
	if (!repo)
		return NULL;

	// Make the package
	PakfirePackage pkg = pakfire_archive_make_package(self->archive, repo);

	// Make the Python object
	PyObject* ret = new_package(&PackageType, pkg);
	printf("ret = %p\n", ret);

	// Cleanup
	pakfire_package_unref(pkg);
	pakfire_repo_unref(repo);
	pakfire_unref(pakfire);

	return ret;
}

static struct PyMethodDef Archive_methods[] = {
	{
		"extract",
		(PyCFunction)Archive_extract,
		METH_VARARGS,
		NULL
	},
	{
		"get_package",
		(PyCFunction)Archive_get_package,
		METH_NOARGS,
		NULL
	},
	{
		"read",
		(PyCFunction)Archive_read,
		METH_VARARGS|METH_KEYWORDS,
		NULL
	},
	{
		"verify",
		(PyCFunction)Archive_verify,
		METH_NOARGS,
		NULL
	},
	{ NULL },
};

static struct PyGetSetDef Archive_getsetters[] = {
	{
		"format",
		(getter)Archive_get_format,
		NULL,
		NULL,
		NULL
	},
	{
		"signatures",
		(getter)Archive_get_signatures,
		NULL,
		NULL,
		NULL
	},
	{ NULL },
};

PyTypeObject ArchiveType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Archive",
	tp_basicsize:       sizeof(ArchiveObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Archive_new,
	tp_dealloc:         (destructor)Archive_dealloc,
	tp_init:            (initproc)Archive_init,
	tp_doc:             "Archive object",
	tp_methods:         Archive_methods,
	tp_getset:          Archive_getsetters,
	//tp_hash:            (hashfunc)Archive_hash,
	//tp_repr:            (reprfunc)Archive_repr,
	//tp_str:             (reprfunc)Archive_str,
	//tp_richcompare:     (richcmpfunc)Archive_richcompare,
};

// Archive Signature

static PyObject* ArchiveSignature_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	ArchiveSignatureObject* self = (ArchiveSignatureObject *)type->tp_alloc(type, 0);
	if (self) {
		self->signature = NULL;
	}

	return (PyObject *)self;
}

PyObject* new_archive_signature(ArchiveObject* archive, PakfireArchiveSignature signature) {
	ArchiveSignatureObject* s = (ArchiveSignatureObject*)ArchiveSignature_new(&ArchiveSignatureType, NULL, NULL);
	if (s)
		s->signature = pakfire_archive_signature_ref(signature);

	return (PyObject *)s;
}

static void ArchiveSignature_dealloc(ArchiveSignatureObject* self) {
	if (self->signature)
		pakfire_archive_signature_unref(self->signature);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject* ArchiveSignature_str(ArchiveSignatureObject* self) {
	const char* data = pakfire_archive_signature_get_data(self->signature);

	return PyUnicode_FromString(data);
}

static struct PyGetSetDef ArchiveSignature_getsetters[] = {
	{ NULL },
};

PyTypeObject ArchiveSignatureType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.ArchiveSignature",
	tp_basicsize:       sizeof(ArchiveSignatureObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             ArchiveSignature_new,
	tp_dealloc:         (destructor)ArchiveSignature_dealloc,
	tp_doc:             "ArchiveSignature object",
	tp_getset:          ArchiveSignature_getsetters,
	tp_str:             (reprfunc)ArchiveSignature_str,
};
