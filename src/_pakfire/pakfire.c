/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2017 Pakfire development team                                 #
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

#include <pakfire/constants.h>
#include <pakfire/execute.h>
#include <pakfire/logging.h>
#include <pakfire/packagelist.h>
#include <pakfire/pakfire.h>
#include <pakfire/key.h>
#include <pakfire/repo.h>
#include <pakfire/util.h>

#include "errors.h"
#include "key.h"
#include "pakfire.h"
#include "repo.h"
#include "util.h"

static PyObject* Pakfire_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	PakfireObject* self = (PakfireObject *)type->tp_alloc(type, 0);
	if (self) {
		self->pakfire = NULL;
	}

	return (PyObject *)self;
}

static int Pakfire_init(PakfireObject* self, PyObject* args, PyObject* kwds) {
	const char* path = NULL;
    const char* arch = NULL;

	if (!PyArg_ParseTuple(args, "s|z", &path, &arch))
		return -1;

	// Create a new Pakfire instance
	int r = pakfire_create(&self->pakfire, path, arch);
	if (r) {
		switch (r) {
			// Invalid architecture
			case -EINVAL:
				PyErr_SetString(PyExc_ValueError, "Invalid architecture or path");
				break;

			// path does not exist
			case -ENOENT:
				PyErr_Format(PyExc_FileNotFoundError,
					"%s does not exist or is not a directory", path);
				break;

			// Anything else
			default:
				PyErr_SetNone(PyExc_OSError);
		}

		return -1;
    }

	return 0;
}

static void Pakfire_dealloc(PakfireObject* self) {
	if (self->pakfire)
		pakfire_unref(self->pakfire);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject* Pakfire_repr(PakfireObject* self) {
    const char* path = pakfire_get_path(self->pakfire);
    const char* arch = pakfire_get_arch(self->pakfire);

	return PyUnicode_FromFormat("<_pakfire.Pakfire %s (%s)>", path, arch);
}

static PyObject* Pakfire_log(PakfireObject* self, PyObject* args, PyObject* kwds) {
	char* kwlist[] = { "priority", "message", "filename", "lineno", "function", NULL };

	int priority;
	const char* message;

	const char* filename = NULL;
	int lineno = 0;
	const char* function = NULL;

	if (!PyArg_ParseTupleAndKeywords(args, kwds, "is|sis", kwlist, &priority, &message,
			&filename, &lineno, &function))
		return NULL;

	// Send message to the pakfire logger
	if (pakfire_log_get_priority(self->pakfire) >= priority)
		pakfire_log(self->pakfire, priority, filename, lineno, function, "%s\n", message);

	Py_RETURN_NONE;
}

static PyObject* Pakfire_get_path(PakfireObject* self) {
    const char* path = pakfire_get_path(self->pakfire);

    return PyUnicode_FromString(path);
}

static PyObject* Pakfire_get_arch(PakfireObject* self) {
    const char* arch = pakfire_get_arch(self->pakfire);

    return PyUnicode_FromString(arch);
}

static PyObject* Pakfire_get_repo(PakfireObject* self, PyObject* args) {
	const char* name = NULL;

	if (!PyArg_ParseTuple(args, "s", &name))
		return NULL;

	PakfireRepo repo = pakfire_get_repo(self->pakfire, name);
	if (!repo)
		Py_RETURN_NONE;

	PyObject* obj = new_repo(&RepoType, repo);
	pakfire_repo_unref(repo);

	return obj;
}

static PyObject* Pakfire_get_cache_path(PakfireObject* self) {
	char* path = pakfire_get_cache_path(self->pakfire, NULL);
	if (!path)
		Py_RETURN_NONE;

	PyObject* obj = PyUnicode_FromString(path);
	pakfire_free(path);

	return obj;
}

static int Pakfire_set_cache_path(PakfireObject* self, PyObject* value) {
	const char* path = PyUnicode_AsUTF8(value);

	if (path)
		pakfire_set_cache_path(self->pakfire, path);

	return 0;
}

static PyObject* Pakfire_get_installed_repo(PakfireObject* self) {
	PakfireRepo repo = pakfire_get_installed_repo(self->pakfire);
	if (!repo)
		Py_RETURN_NONE;

	PyObject* obj = new_repo(&RepoType, repo);
	pakfire_repo_unref(repo);

	return obj;
}

static int Pakfire_set_installed_repo(PakfireObject* self, PyObject* value) {
#if 0
	if (PyObject_Not(value)) {
		pakfire_pool_set_installed_repo(self->pool, NULL);
		return 0;
	}
#endif

	if (!PyObject_TypeCheck(value, &RepoType)) {
		PyErr_SetString(PyExc_ValueError, "Argument must be a _pakfire.Repo object");
		return -1;
	}

	RepoObject* repo = (RepoObject *)value;
	pakfire_set_installed_repo(self->pakfire, repo->repo);

	return 0;
}

static PyObject* _import_keylist(PakfireObject* pakfire, PakfireKey* keys) {
	PyObject* list = PyList_New(0);

	while (keys && *keys) {
		PakfireKey key = *keys++;

		PyObject* object = new_key(&KeyType, key);
		PyList_Append(list, object);

		// Drop reference to the Python object
		Py_DECREF(object);

		// Drop reference to the key object
		pakfire_key_unref(key);
	}

	return list;
}

static PyObject* Pakfire_get_keys(PakfireObject* self) {
	PakfireKey* keys = pakfire_key_list(self->pakfire);

	return _import_keylist(self, keys);
}

static PyObject* Pakfire_get_key(PakfireObject* self, PyObject* args) {
	const char* pattern = NULL;

	if (!PyArg_ParseTuple(args, "s", &pattern))
		return NULL;

	PakfireKey key = pakfire_key_get(self->pakfire, pattern);
	if (!key)
		Py_RETURN_NONE;

	return new_key(&KeyType, key);
}

static PyObject* Pakfire_generate_key(PakfireObject* self, PyObject* args) {
	const char* userid = NULL;

	if (!PyArg_ParseTuple(args, "s", &userid))
		return NULL;

	PakfireKey key = pakfire_key_generate(self->pakfire, userid);
	assert(key);

	return new_key(&KeyType, key);
}

static PyObject* Pakfire_import_key(PakfireObject* self, PyObject* args) {
	const char* data = NULL;

	if (!PyArg_ParseTuple(args, "s", &data))
		return NULL;

	PakfireKey* keys = pakfire_key_import(self->pakfire, data);
	if (!keys)
		return NULL; // TODO Raise error from errno

	return _import_keylist(self, keys);
}

static PyObject* Pakfire_whatprovides(PakfireObject* self, PyObject* args, PyObject* kwds) {
	char* kwlist[] = {"provides", "glob", "icase", "name_only", NULL};

	const char* provides;
	int glob = 0;
	int icase = 0;
	int name_only = 0;

	if (!PyArg_ParseTupleAndKeywords(args, kwds, "s|iii", kwlist, &provides, &glob, &icase, &name_only))
		return NULL;

	int flags = 0;
	if (glob)
		flags |= PAKFIRE_GLOB;
	if (icase)
		flags |= PAKFIRE_ICASE;
	if (name_only)
		flags |= PAKFIRE_NAME_ONLY;

	PakfirePackageList list = pakfire_whatprovides(self->pakfire, provides, flags);

	PyObject* obj = PyList_FromPackageList(list);
	pakfire_packagelist_unref(list);

	return obj;
}

static PyObject* Pakfire_search(PakfireObject* self, PyObject* args) {
	const char* what;

	if (!PyArg_ParseTuple(args, "s", &what))
		return NULL;

	PakfirePackageList list = pakfire_search(self->pakfire, what, 0);

	PyObject* obj = PyList_FromPackageList(list);
	pakfire_packagelist_unref(list);

	return obj;
}

static PyObject* Pakfire_version_compare(PakfireObject* self, PyObject* args) {
	const char* evr1 = NULL;
	const char* evr2 = NULL;

	if (!PyArg_ParseTuple(args, "ss", &evr1, &evr2))
		return NULL;

	int cmp = pakfire_version_compare(self->pakfire, evr1, evr2);

	return PyLong_FromLong(cmp);
}

static PyObject* Pakfire_get_installonly(PakfireObject* self) {
	const char** installonly = pakfire_get_installonly(self->pakfire);

	PyObject* list = PyList_New(0);
	const char* name;

	while ((name = *installonly++) != NULL) {
		PyObject* item = PyUnicode_FromString(name);
		PyList_Append(list, item);

		Py_DECREF(item);
	}

	Py_INCREF(list);
	return list;
}

static int Pakfire_set_installonly(PakfireObject* self, PyObject* value) {
	if (!PySequence_Check(value)) {
		PyErr_SetString(PyExc_AttributeError, "Expected a sequence.");
		return -1;
	}

	const int length = PySequence_Length(value);
	const char* installonly[length + 1];

	for (int i = 0; i < length; i++) {
		PyObject* item = PySequence_GetItem(value, i);

		installonly[i] = PyUnicode_AsUTF8(item);
		Py_DECREF(item);
	}
	installonly[length] = NULL;

	pakfire_set_installonly(self->pakfire, installonly);

	return 0;
}

static Py_ssize_t Pakfire_len(PakfireObject* self) {
	return pakfire_count_packages(self->pakfire);
}

static PyObject* Pakfire_execute(PakfireObject* self, PyObject* args, PyObject* kwds) {
	char* kwlist[] = {"command", "environ", NULL};

	PyObject* command = NULL;
	PyObject* environ = NULL;

	if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|O", kwlist, &command, &environ))
		return NULL;

	// Check if command is a list
	if (!PyList_Check(command)) {
		PyErr_SetString(PyExc_TypeError, "command must be a list");
		return NULL;
	}

	ssize_t command_length = PyList_Size(command);

	// Check if command is not empty
	if (command_length == 0) {
		PyErr_SetString(PyExc_ValueError, "command is empty");
		return NULL;
	}

	// All arguments in command must be strings
	for (unsigned int i = 0; i < command_length; i++) {
		PyObject* item = PyList_GET_ITEM(command, i);

		if (!PyUnicode_Check(item)) {
			PyErr_Format(PyExc_TypeError, "Item %u in command is not a string", i);
			return NULL;
		}
	}

	ssize_t environ_length = 0;
	PyObject* key;
	PyObject* value;
	Py_ssize_t p = 0;

	if (environ) {
		// Check if environ is a dictionary
		if (!PyDict_Check(environ)) {
			PyErr_SetString(PyExc_TypeError, "environ must be a dictionary");
			return NULL;
		}

		// All keys and values must be strings
		while (PyDict_Next(environ, &p, &key, &value)) {
			if (!PyUnicode_Check(key) || !PyUnicode_Check(value)) {
				PyErr_SetString(PyExc_TypeError, "Environment contains a non-string object");
				return NULL;
			}
		}

		environ_length = PyDict_Size(environ);
	}

	// All inputs look fine

	const char* argv[command_length + 1];
	char* envp[environ_length + 1];

	// Parse arguments
	for (unsigned int i = 0; i < command_length; i++) {
		PyObject* item = PyList_GET_ITEM(command, i);
		argv[i] = PyUnicode_AsUTF8(item);
	}

	// Parse environ
	if (environ) {
		unsigned int i = 0;
		p = 0;

		while (PyDict_Next(environ, &p, &key, &value)) {
			int r = asprintf(&envp[i++], "%s=%s",
				PyUnicode_AsUTF8(key), PyUnicode_AsUTF8(value));

			// Handle errors
			if (r < 0) {
				// Cleanup
				for (unsigned int i = 0; envp[i]; i++)
					free(envp[i]);

				return PyErr_NoMemory();
			}
		}
	}

	// Terminate argv and envp
	argv[command_length] = NULL;
	envp[environ_length] = NULL;

	// Execute command
	int r = pakfire_execute(self->pakfire, argv[0], argv, (const char**)envp, 0);

	// Cleanup
	for (unsigned int i = 0; envp[i]; i++)
		free(envp[i]);

	// Raise exception when the command failed
	if (r) {
		PyObject* code = PyLong_FromLong(r);

		PyErr_SetObject(PyExc_CommandExecutionError, code);
		Py_DECREF(code);

		return NULL;
	}

	// Return nothing
	Py_RETURN_NONE;
}

static struct PyMethodDef Pakfire_methods[] = {
	{
		"execute",
		(PyCFunction)Pakfire_execute,
		METH_VARARGS|METH_KEYWORDS,
		NULL
	},
	{
		"generate_key",
		(PyCFunction)Pakfire_generate_key,
		METH_VARARGS,
		NULL
	},
	{
		"get_key",
		(PyCFunction)Pakfire_get_key,
		METH_VARARGS,
		NULL
	},
	{
		"get_repo",
		(PyCFunction)Pakfire_get_repo,
		METH_VARARGS,
		NULL
	},
	{
		"import_key",
		(PyCFunction)Pakfire_import_key,
		METH_VARARGS,
		NULL
	},
	{
		"search",
		(PyCFunction)Pakfire_search,
		METH_VARARGS,
		NULL
	},
	{
		"version_compare",
		(PyCFunction)Pakfire_version_compare,
		METH_VARARGS,
		NULL
	},
	{
		"whatprovides",
		(PyCFunction)Pakfire_whatprovides,
		METH_VARARGS|METH_KEYWORDS,
		NULL
	},
	{
		"_log",
		(PyCFunction)Pakfire_log,
		METH_VARARGS|METH_KEYWORDS,
		NULL
	},
	{ NULL },
};

static struct PyGetSetDef Pakfire_getsetters[] = {
	{
		"arch",
		(getter)Pakfire_get_arch,
		NULL,
		NULL,
		NULL
	},
	{
		"cache_path",
		(getter)Pakfire_get_cache_path,
		(setter)Pakfire_set_cache_path,
		NULL,
		NULL
	},
	{
		"installed_repo",
		(getter)Pakfire_get_installed_repo,
		(setter)Pakfire_set_installed_repo,
		NULL,
		NULL
	},
	{
		"installonly",
		(getter)Pakfire_get_installonly,
		(setter)Pakfire_set_installonly,
		NULL,
		NULL
	},
	{
		"keys",
		(getter)Pakfire_get_keys,
		NULL,
		NULL,
		NULL
	},
    {
		"path",
		(getter)Pakfire_get_path,
		NULL,
		NULL,
		NULL
	},
    { NULL },
};

static PySequenceMethods Pakfire_sequence = {
	sq_length:          (lenfunc)Pakfire_len,
};

PyTypeObject PakfireType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Pakfire",
	tp_basicsize:       sizeof(PakfireObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Pakfire_new,
	tp_dealloc:         (destructor)Pakfire_dealloc,
	tp_init:            (initproc)Pakfire_init,
	tp_doc:             "Pakfire object",
	tp_methods:         Pakfire_methods,
	tp_getset:          Pakfire_getsetters,
	tp_repr:            (reprfunc)Pakfire_repr,
	tp_as_sequence:     &Pakfire_sequence,
};
