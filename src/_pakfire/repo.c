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

#include <pakfire/errno.h>
#include <pakfire/package.h>
#include <pakfire/repo.h>
#include <pakfire/util.h>

#include "package.h"
#include "repo.h"

PyObject* new_repo(PyTypeObject* type, PakfireRepo repo) {
	RepoObject* self = (RepoObject *)type->tp_alloc(type, 0);
	if (self) {
		self->repo = pakfire_repo_ref(repo);
	}

	return (PyObject*)self;
}

static PyObject* Repo_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	RepoObject* self = (RepoObject *)type->tp_alloc(type, 0);
	if (self) {
		self->repo = NULL;
	}

	return (PyObject *)self;
}

static void Repo_dealloc(RepoObject* self) {
	pakfire_repo_unref(self->repo);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Repo_init(RepoObject* self, PyObject* args, PyObject* kwds) {
	PakfireObject* pakfire;
	const char* name;

	if (!PyArg_ParseTuple(args, "O!s", &PakfireType, &pakfire, &name))
		return -1;

	// Create a new repository
	self->repo = pakfire_repo_create(pakfire->pakfire, name);

	return 0;
}

static long Repo_hash(RepoObject* self) {
	return (long)self->repo;
}

static PyObject* Repo_richcompare(RepoObject* self, RepoObject* other, int op) {
	int r;

	switch (op) {
		case Py_EQ:
			if (pakfire_repo_identical(self->repo, other->repo) == 0)
				Py_RETURN_TRUE;

			Py_RETURN_FALSE;
			break;

		case Py_LT:
			r = pakfire_repo_cmp(self->repo, other->repo);
			if (r < 0)
				Py_RETURN_TRUE;

			Py_RETURN_FALSE;
			break;

		default:
			break;
	}

	Py_RETURN_NOTIMPLEMENTED;
}

static Py_ssize_t Repo_len(RepoObject* self) {
	return pakfire_repo_count(self->repo);
}

static PyObject* Repo_get_name(RepoObject* self) {
	const char* name = pakfire_repo_get_name(self->repo);

	return PyUnicode_FromString(name);
}

static int Repo_set_name(RepoObject* self, PyObject* value) {
	const char* name = PyUnicode_AsUTF8(value);

	pakfire_repo_set_name(self->repo, name);
	return 0;
}

static PyObject* Repo_get_enabled(RepoObject* self) {
	if (pakfire_repo_get_enabled(self->repo))
		Py_RETURN_TRUE;

	Py_RETURN_FALSE;
}

static int Repo_set_enabled(RepoObject* self, PyObject* value) {
	if (PyObject_IsTrue(value))
		pakfire_repo_set_enabled(self->repo, 1);
	else
		pakfire_repo_set_enabled(self->repo, 0);

	return 0;
}

static PyObject* Repo_get_priority(RepoObject* self) {
	int priority = pakfire_repo_get_priority(self->repo);

	return PyLong_FromLong(priority);
}

static int Repo_set_priority(RepoObject* self, PyObject* value) {
	long priority = PyLong_AsLong(value);

	if (priority > INT_MAX || priority < INT_MIN)
		return -1;

	pakfire_repo_set_priority(self->repo, priority);
	return 0;
}

static PyObject* Repo_get_baseurl(RepoObject* self) {
	const char* baseurl = pakfire_repo_get_baseurl(self->repo);

	return PyUnicode_FromString(baseurl);
}

static int Repo_set_baseurl(RepoObject* self, PyObject* value) {
	const char* baseurl = PyUnicode_AsUTF8(value);

	return pakfire_repo_set_baseurl(self->repo, baseurl);
}

static PyObject* Repo_get_keyfile(RepoObject* self) {
	const char* keyfile = pakfire_repo_get_keyfile(self->repo);

	return PyUnicode_FromString(keyfile);
}

static int Repo_set_keyfile(RepoObject* self, PyObject* value) {
	const char* keyfile = NULL;

	if (value != Py_None)
		keyfile = PyUnicode_AsUTF8(value);

	return pakfire_repo_set_keyfile(self->repo, keyfile);
}

static PyObject* Repo_read_solv(RepoObject* self, PyObject* args) {
	const char* filename = NULL;

	if (!PyArg_ParseTuple(args, "s", &filename))
		return NULL;

	int ret = pakfire_repo_read_solv(self->repo, filename, 0);

	switch (ret) {
		case 0:
			Py_RETURN_NONE;
			break;

		case PAKFIRE_E_SOLV_NOT_SOLV:
			PyErr_Format(PyExc_ValueError, "File not in SOLV format: %s", filename);
			break;

		case PAKFIRE_E_SOLV_UNSUPPORTED:
			PyErr_Format(PyExc_ValueError, "File in an unsupported version"
				" of the SOLV format: %s", filename);
			break;

		case PAKFIRE_E_SOLV_CORRUPTED:
			PyErr_Format(PyExc_ValueError, "SOLV file is corrupted: %s", filename);
			break;

		case PAKFIRE_E_IO:
			PyErr_Format(PyExc_IOError, "Could not read file %s: %s", filename, strerror(errno));
			break;

		default:
			PyErr_Format(PyExc_RuntimeError, "pakfire_repo_read() failed: %s", ret);
			break;
	}

	return NULL;
}

static PyObject* Repo_write_solv(RepoObject* self, PyObject* args) {
	const char* filename = NULL;

	if (!PyArg_ParseTuple(args, "s", &filename))
		return NULL;

	int ret = pakfire_repo_write_solv(self->repo, filename, 0);

	switch (ret) {
		case 0:
			Py_RETURN_NONE;
			break;

		case PAKFIRE_E_IO:
			PyErr_Format(PyExc_IOError, "Could not open file %s", filename);
			break;

		default:
			PyErr_Format(PyExc_RuntimeError, "pakfire_repo_write() failed: %d", ret);
			break;
	}

	return NULL;
}

static PyObject* Repo__add_package(RepoObject* self, PyObject* args) {
	const char* name;
	const char* evr;
	const char* arch;

	if (!PyArg_ParseTuple(args, "sss", &name, &evr, &arch))
		return NULL;

	Pakfire pakfire = pakfire_repo_get_pakfire(self->repo);
	PakfirePackage pkg = pakfire_package_create2(pakfire, self->repo, name, evr, arch);

	PyObject* obj = new_package(&PackageType, pkg);

	pakfire_package_unref(pkg);
	pakfire_unref(pakfire);

	return obj;
}

static PyObject* Repo_cache_age(RepoObject* self, PyObject* args) {
	const char* path = NULL;

	if (!PyArg_ParseTuple(args, "s", &path))
		return NULL;

	time_t age = pakfire_repo_cache_age(self->repo, path);
	if (age < 0)
		Py_RETURN_NONE;

	return PyLong_FromLong(age);
}

static PyObject* Repo_cache_exists(RepoObject* self, PyObject* args) {
	const char* path = NULL;

	if (!PyArg_ParseTuple(args, "s", &path))
		return NULL;

	int r = pakfire_repo_cache_access(self->repo, path, F_OK);
	if (r == 0)
		Py_RETURN_TRUE;

	Py_RETURN_FALSE;
}

static PyObject* Repo_cache_open(RepoObject* self, PyObject* args) {
	const char* path = NULL;
	const char* mode = NULL;

	if (!PyArg_ParseTuple(args, "ss", &path, &mode))
		return NULL;

	FILE* f = pakfire_repo_cache_open(self->repo, path, mode);
	if (!f) {
		PyErr_Format(PyExc_IOError, "Could not open file %s: %s", path, strerror(errno));
		return NULL;
	}

	// XXX might cause some problems with internal buffering
	return PyFile_FromFd(fileno(f), NULL, mode, 1, NULL, NULL, NULL, 1);
}

static PyObject* Repo_cache_path(RepoObject* self, PyObject* args) {
	const char* path = NULL;

	if (!PyArg_ParseTuple(args, "s", &path))
		return NULL;

	char* cache_path = pakfire_repo_cache_get_path(self->repo, path);

	PyObject* obj = PyUnicode_FromString(cache_path);
	pakfire_free(cache_path);

	return obj;
}

static PyObject* Repo_clean(RepoObject* self, PyObject* args) {
	int r = pakfire_repo_clean(self->repo);

	if (r) {
		PyErr_SetFromErrno(PyExc_OSError);
		return NULL;
	}

	Py_RETURN_NONE;
}

static struct PyMethodDef Repo_methods[] = {
	{
		"cache_age",
		(PyCFunction)Repo_cache_age,
		METH_VARARGS,
		NULL
	},
	{
		"cache_exists",
		(PyCFunction)Repo_cache_exists,
		METH_VARARGS,
		NULL
	},
	{
		"cache_open",
		(PyCFunction)Repo_cache_open,
		METH_VARARGS,
		NULL
	},
	{
		"cache_path",
		(PyCFunction)Repo_cache_path,
		METH_VARARGS,
		NULL
	},
	{
		"clean",
		(PyCFunction)Repo_clean,
		METH_VARARGS,
		NULL,
	},
	{
		"read_solv",
		(PyCFunction)Repo_read_solv,
		METH_VARARGS,
		NULL
	},
	{
		"write_solv",
		(PyCFunction)Repo_write_solv,
		METH_VARARGS,
		NULL
	},
	{
		"_add_package",
		(PyCFunction)Repo__add_package,
		METH_VARARGS,
		NULL
	},
	{ NULL }
};

static struct PyGetSetDef Repo_getsetters[] = {
	{
		"baseurl",
		(getter)Repo_get_baseurl,
		(setter)Repo_set_baseurl,
		"The base URL of this repository",
		NULL
	},
	{
		"keyfile",
		(getter)Repo_get_keyfile,
		(setter)Repo_set_keyfile,
		NULL,
		NULL
	},
	{
		"name",
		(getter)Repo_get_name,
		(setter)Repo_set_name,
		"The name of the repository",
		NULL
	},
	{
		"enabled",
		(getter)Repo_get_enabled,
		(setter)Repo_set_enabled,
		NULL,
		NULL
	},
	{
		"priority",
		(getter)Repo_get_priority,
		(setter)Repo_set_priority,
		"The priority of the repository",
		NULL
	},
	{ NULL }
};

static PySequenceMethods Repo_sequence = {
	sq_length:          (lenfunc)Repo_len,
};

PyTypeObject RepoType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Repo",
	tp_basicsize:       sizeof(RepoObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Repo_new,
	tp_dealloc:         (destructor)Repo_dealloc,
	tp_init:            (initproc)Repo_init,
	tp_doc:             "Repo object",
	tp_methods:         Repo_methods,
	tp_getset:          Repo_getsetters,
	tp_as_sequence:     &Repo_sequence,
	tp_hash:            (hashfunc)Repo_hash,
	tp_richcompare:     (richcmpfunc)Repo_richcompare,
};
