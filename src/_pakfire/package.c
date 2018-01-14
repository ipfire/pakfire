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

#include <pakfire/file.h>
#include <pakfire/package.h>
#include <pakfire/relationlist.h>
#include <pakfire/util.h>

#include "package.h"
#include "relation.h"
#include "repo.h"

PyObject* new_package(PoolObject* pool, Id id) {
	PyObject* args = Py_BuildValue("Oi", (PyObject *)pool, id);
	PyObject* repo = PyObject_CallObject((PyObject *)&PackageType, args);

	Py_DECREF(args);

	return repo;
}

static PyObject* Package_new(PyTypeObject* type, PyObject* args, PyObject* kwds) {
	PackageObject* self = (PackageObject *)type->tp_alloc(type, 0);
	if (self) {
		self->pool = NULL;
		self->package = NULL;
	}

	return (PyObject *)self;
}

static void Package_dealloc(PackageObject* self) {
	if (self->package)
		pakfire_package_unref(self->package);

	Py_TYPE(self)->tp_free((PyObject *)self);
}

static int Package_init(PackageObject* self, PyObject* args, PyObject* kwds) {
	PyObject* pool;
	int id = 0;

	if (!PyArg_ParseTuple(args, "O!|i", &PoolType, &pool, &id))
		return -1;

	self->pool = (PoolObject *)pool;
	Py_INCREF(self->pool);

	self->package = pakfire_package_create(self->pool->pool, (Id)id);

	return 0;
}

static long Package_hash(PackageObject* self) {
	return pakfire_package_id(self->package);
}

static PyObject* Package_repr(PackageObject* self) {
	char* nevra = pakfire_package_get_nevra(self->package);

	PyObject* repr = PyUnicode_FromFormat("<_pakfire.Package object id %ld, %s>",
		Package_hash(self), nevra);
	pakfire_free(nevra);

	return repr;
}

static PyObject* Package_str(PackageObject* self) {
	char* nevra = pakfire_package_get_nevra(self->package);

	PyObject* str = PyUnicode_FromString(nevra);
	pakfire_free(nevra);

	return str;
}

static PyObject* Package_richcompare(PackageObject* self, PyObject* _other, int op) {
	if (!PyType_IsSubtype(_other->ob_type, &PackageType)) {
		PyErr_SetString(PyExc_TypeError, "Expected a Package object");
		return NULL;
	}

	PackageObject* other = (PackageObject *)_other;

	long result = pakfire_package_cmp(self->package, other->package);

	switch (op) {
		case Py_EQ:
			if (result == 0)
				Py_RETURN_TRUE;
			break;

		case Py_NE:
			if (result != 0)
				Py_RETURN_TRUE;
			break;

		case Py_LE:
			if (result <= 0)
				Py_RETURN_TRUE;
			break;

		case Py_GE:
			if (result >= 0)
				Py_RETURN_TRUE;
			break;

		case Py_LT:
			if (result < 0)
				Py_RETURN_TRUE;
			break;

		case Py_GT:
			if (result > 0)
				Py_RETURN_TRUE;
			break;

		default:
			PyErr_BadArgument();
			return NULL;
	}

	Py_RETURN_FALSE;
}

static const char* PyUnicode_FromValue(PyObject* value) {
	if (value == Py_None)
		return NULL;

	return PyUnicode_AsUTF8(value);
}

static PyObject* Package_get_name(PackageObject* self) {
	const char* name = pakfire_package_get_name(self->package);
	if (!name)
		Py_RETURN_NONE;

	return PyUnicode_FromString(name);
}

static void Package_set_name(PackageObject* self, PyObject* value) {
	const char* name = PyUnicode_FromValue(value);

	pakfire_package_set_name(self->package, name);
}

static PyObject* Package_get_epoch(PackageObject* self) {
	unsigned long epoch = pakfire_package_get_epoch(self->package);

	return PyLong_FromLong(epoch);
}

static PyObject* Package_get_version(PackageObject* self) {
	const char* version = pakfire_package_get_version(self->package);
	if (!version)
		Py_RETURN_NONE;

	return PyUnicode_FromString(version);
}

static PyObject* Package_get_release(PackageObject* self) {
	const char* release = pakfire_package_get_release(self->package);
	if (!release)
		Py_RETURN_NONE;

	return PyUnicode_FromString(release);
}

static PyObject* Package_get_evr(PackageObject* self) {
	const char* evr = pakfire_package_get_evr(self->package);
	if (!evr)
		Py_RETURN_NONE;

	return PyUnicode_FromString(evr);
}

static PyObject* Package_get_arch(PackageObject* self) {
	const char* arch = pakfire_package_get_arch(self->package);
	if (!arch)
		Py_RETURN_NONE;

	return PyUnicode_FromString(arch);
}

static void Package_set_arch(PackageObject* self, PyObject* value) {
	const char* arch = PyUnicode_FromValue(value);

	pakfire_package_set_arch(self->package, arch);
}

static PyObject* Package_get_uuid(PackageObject* self) {
	const char* uuid = pakfire_package_get_uuid(self->package);
	if (!uuid)
		Py_RETURN_NONE;

	return PyUnicode_FromString(uuid);
}

static void Package_set_uuid(PackageObject* self, PyObject* value) {
	const char* uuid = PyUnicode_FromValue(value);

	pakfire_package_set_uuid(self->package, uuid);
}

static PyObject* Package_get_checksum(PackageObject* self) {
	const char* checksum = pakfire_package_get_checksum(self->package);
	if (!checksum)
		Py_RETURN_NONE;

	return PyUnicode_FromString(checksum);
}

static void Package_set_checksum(PackageObject* self, PyObject* value) {
	const char* checksum = PyUnicode_FromValue(value);

	pakfire_package_set_checksum(self->package, checksum);
}

static PyObject* Package_get_summary(PackageObject* self) {
	const char* summary = pakfire_package_get_summary(self->package);
	if (!summary)
		Py_RETURN_NONE;

	return PyUnicode_FromString(summary);
}

static void Package_set_summary(PackageObject* self, PyObject* value) {
	const char* summary = PyUnicode_FromValue(value);

	pakfire_package_set_summary(self->package, summary);
}

static PyObject* Package_get_description(PackageObject* self) {
	const char* description = pakfire_package_get_description(self->package);
	if (!description)
		Py_RETURN_NONE;

	return PyUnicode_FromString(description);
}

static void Package_set_description(PackageObject* self, PyObject* value) {
	const char* description = PyUnicode_FromValue(value);

	pakfire_package_set_description(self->package, description);
}

static PyObject* Package_get_license(PackageObject* self) {
	const char* license = pakfire_package_get_license(self->package);
	if (!license)
		Py_RETURN_NONE;

	return PyUnicode_FromString(license);
}

static void Package_set_license(PackageObject* self, PyObject* value) {
	const char* license = PyUnicode_FromValue(value);

	pakfire_package_set_summary(self->package, license);
}

static PyObject* Package_get_url(PackageObject* self) {
	const char* url = pakfire_package_get_url(self->package);
	if (!url)
		Py_RETURN_NONE;

	return PyUnicode_FromString(url);
}

static void Package_set_url(PackageObject* self, PyObject* value) {
	const char* url = PyUnicode_FromValue(value);

	pakfire_package_set_url(self->package, url);
}

static PyObject* Package_get_groups(PackageObject* self) {
	const char** groups = pakfire_package_get_groups(self->package);

	PyObject* list = PyList_New(0);
	const char* group;

	while ((group = *groups++) != NULL) {
		PyObject* item = PyUnicode_FromString(group);
		PyList_Append(list, item);

		Py_DECREF(item);
	}

	Py_INCREF(list);
	return list;
}

static int Package_set_groups(PackageObject* self, PyObject* value) {
	if (!PySequence_Check(value)) {
		PyErr_SetString(PyExc_AttributeError, "Expected a sequence.");
		return -1;
	}

	const int length = PySequence_Length(value);
	const char* groups[length + 1];

	for (int i = 0; i < length; i++) {
		PyObject* item = PySequence_GetItem(value, i);
		groups[i] = PyUnicode_AsUTF8(item);

		Py_DECREF(item);
	}
	groups[length] = NULL;

	pakfire_package_set_groups(self->package, groups);

	return 0;
}

static PyObject* Package_get_vendor(PackageObject* self) {
	const char* vendor = pakfire_package_get_vendor(self->package);
	if (!vendor)
		Py_RETURN_NONE;

	return PyUnicode_FromString(vendor);
}

static void Package_set_vendor(PackageObject* self, PyObject* value) {
	const char* vendor = PyUnicode_FromValue(value);

	pakfire_package_set_vendor(self->package, vendor);
}

static PyObject* Package_get_maintainer(PackageObject* self) {
	const char* maintainer = pakfire_package_get_maintainer(self->package);
	if (!maintainer)
		Py_RETURN_NONE;

	return PyUnicode_FromString(maintainer);
}

static void Package_set_maintainer(PackageObject* self, PyObject* value) {
	const char* maintainer = PyUnicode_FromValue(value);

	pakfire_package_set_maintainer(self->package, maintainer);
}

static PyObject* Package_get_filename(PackageObject* self) {
	const char* filename = pakfire_package_get_filename(self->package);
	if (!filename)
		Py_RETURN_NONE;

	return PyUnicode_FromString(filename);
}

static void Package_set_filename(PackageObject* self, PyObject* value) {
	const char* filename = PyUnicode_FromValue(value);

	pakfire_package_set_filename(self->package, filename);
}

static PyObject* Package_get_installed(PackageObject* self) {
	int installed = pakfire_package_is_installed(self->package);

	return PyBool_FromLong(installed);
}

static PyObject* Package_get_downloadsize(PackageObject* self) {
	unsigned long long size = pakfire_package_get_downloadsize(self->package);

	return PyLong_FromUnsignedLongLong(size);
}

static void Package_set_downloadsize(PackageObject* self, PyObject* value) {
	unsigned long downloadsize = PyLong_AsUnsignedLong(value);

	pakfire_package_set_downloadsize(self->package, downloadsize);
}

static PyObject* Package_get_installsize(PackageObject* self) {
	unsigned long long size = pakfire_package_get_installsize(self->package);

	return PyLong_FromUnsignedLongLong(size);
}

static void Package_set_installsize(PackageObject* self, PyObject* value) {
	unsigned long installsize = PyLong_AsUnsignedLong(value);

	pakfire_package_set_installsize(self->package, installsize);
}

static PyObject* Package_get_size(PackageObject* self) {
	unsigned long long size = pakfire_package_get_size(self->package);

	return PyLong_FromUnsignedLongLong(size);
}

static PyObject* Package_get_buildhost(PackageObject* self) {
	const char* buildhost = pakfire_package_get_buildhost(self->package);
	if (!buildhost)
		Py_RETURN_NONE;

	return PyUnicode_FromString(buildhost);
}

static void Package_set_buildhost(PackageObject* self, PyObject* value) {
	const char* buildhost = PyUnicode_FromValue(value);

	pakfire_package_set_buildhost(self->package, buildhost);
}

static PyObject* Package_get_buildtime(PackageObject* self) {
	unsigned long long buildtime = pakfire_package_get_buildtime(self->package);

	return PyLong_FromUnsignedLongLong(buildtime);
}

static void Package_set_buildtime(PackageObject* self, PyObject* value) {
	unsigned long long buildtime = PyLong_AsUnsignedLongLong(value);

	pakfire_package_set_buildtime(self->package, buildtime);
}

static PyObject* Package_get_cache_path(PackageObject* self) {
	char* cache_path = pakfire_package_get_cache_path(self->package);
	PyObject* ret = PyUnicode_FromString(cache_path);
	pakfire_free(cache_path);

	return ret;
}

static PyObject* Package_get_cache_full_path(PackageObject* self) {
	char* cache_path = pakfire_package_get_cache_full_path(self->package);
	PyObject* ret = PyUnicode_FromString(cache_path);
	pakfire_free(cache_path);

	return ret;
}

static PyObject* Package_get_repo(PackageObject* self) {
	PakfireRepo repo = pakfire_package_get_repo(self->package);

	if (!repo)
		return NULL;

	const char* name = pakfire_repo_get_name(repo);
	pakfire_repo_free(repo);

	return new_repo(self->pool, name);
}

static int Package_set_repo(PackageObject* self, PyObject* value) {
	#warning TODO Package_set_repo
	return -1;
}

static PyObject* Package_get_location(PackageObject* self) {
	char* location = pakfire_package_get_location(self->package);

	PyObject* str = PyUnicode_FromString(location);
	pakfire_free(location);

	return str;
}

static PyObject* PyList_FromRelationList(PoolObject* pool, PakfireRelationList relationlist) {
	PyObject* list = PyList_New(0);
	if (list == NULL)
		return NULL;

	const int count = pakfire_relationlist_count(relationlist);

	for (int i = 0; i < count; i++) {
		PakfireRelation relation = pakfire_relationlist_get_clone(relationlist, i);
		PyObject* relation_obj = new_relation(pool, pakfire_relation_id(relation));

		pakfire_relation_free(relation);
		if (relation_obj == NULL)
			goto fail;

		int ret = PyList_Append(list, relation_obj);
		Py_DECREF(relation_obj);

		if (ret == -1)
			goto fail;
	}

	return list;

fail:
	Py_DECREF(list);
	return NULL;
}

static PakfireRelationList PyList_AsRelationList(PoolObject* pool, PyObject* value) {
	if (!PySequence_Check(value)) {
		PyErr_SetString(PyExc_AttributeError, "Expected a sequence.");
		return NULL;
	}

	const int length = PySequence_Length(value);
	PakfireRelationList relationlist = pakfire_relationlist_create(pool->pool);

	for (int i = 0; i < length; i++) {
		PyObject* item = PySequence_GetItem(value, i);

		if (!PyObject_TypeCheck(item, &RelationType)) {
			pakfire_relationlist_free(relationlist);
			Py_DECREF(item);

			PyErr_SetString(PyExc_AttributeError, "Expected a Relation object");
			return NULL;
		}

		RelationObject* relation = (RelationObject *)item;
		pakfire_relationlist_add(relationlist, relation->relation);

		Py_DECREF(item);
	}

	return relationlist;
}

static PyObject* Package_get_provides(PackageObject* self) {
	PakfireRelationList relationlist = pakfire_package_get_provides(self->package);

	PyObject* list = PyList_FromRelationList(self->pool, relationlist);
	pakfire_relationlist_free(relationlist);

	return list;
}

static int Package_set_provides(PackageObject* self, PyObject* value) {
	PakfireRelationList relationlist = PyList_AsRelationList(self->pool, value);
	if (!relationlist)
		return -1;

	pakfire_package_set_provides(self->package, relationlist);
	pakfire_relationlist_free(relationlist);

	return 0;
}

static PyObject* Package_add_provides(PackageObject* self, PyObject* args) {
	RelationObject* relation = NULL;

	if (!PyArg_ParseTuple(args, "O!", &RelationType, &relation))
		return NULL;

	pakfire_package_add_provides(self->package, relation->relation);

	Py_RETURN_NONE;
}

static PyObject* Package_get_requires(PackageObject* self) {
	PakfireRelationList relationlist = pakfire_package_get_requires(self->package);

	PyObject* list = PyList_FromRelationList(self->pool, relationlist);
	pakfire_relationlist_free(relationlist);

	return list;
}

static int Package_set_requires(PackageObject* self, PyObject* value) {
	PakfireRelationList relationlist = PyList_AsRelationList(self->pool, value);
	if (!relationlist)
		return -1;

	pakfire_package_set_requires(self->package, relationlist);
	pakfire_relationlist_free(relationlist);

	return 0;
}

static PyObject* Package_add_requires(PackageObject* self, PyObject* args) {
	RelationObject* relation = NULL;

	if (!PyArg_ParseTuple(args, "O!", &RelationType, &relation))
		return NULL;

	pakfire_package_add_requires(self->package, relation->relation);

	Py_RETURN_NONE;
}

static PyObject* Package_get_obsoletes(PackageObject* self) {
	PakfireRelationList relationlist = pakfire_package_get_obsoletes(self->package);

	PyObject* list = PyList_FromRelationList(self->pool, relationlist);
	pakfire_relationlist_free(relationlist);

	return list;
}

static int Package_set_obsoletes(PackageObject* self, PyObject* value) {
	PakfireRelationList relationlist = PyList_AsRelationList(self->pool, value);
	if (!relationlist)
		return -1;

	pakfire_package_set_obsoletes(self->package, relationlist);
	pakfire_relationlist_free(relationlist);

	return 0;
}

static PyObject* Package_add_obsoletes(PackageObject* self, PyObject* args) {
	RelationObject* relation = NULL;

	if (!PyArg_ParseTuple(args, "O!", &RelationType, &relation))
		return NULL;

	pakfire_package_add_obsoletes(self->package, relation->relation);

	Py_RETURN_NONE;
}

static PyObject* Package_get_conflicts(PackageObject* self) {
	PakfireRelationList relationlist = pakfire_package_get_conflicts(self->package);

	PyObject* list = PyList_FromRelationList(self->pool, relationlist);
	pakfire_relationlist_free(relationlist);

	return list;
}

static int Package_set_conflicts(PackageObject* self, PyObject* value) {
	PakfireRelationList relationlist = PyList_AsRelationList(self->pool, value);
	if (!relationlist)
		return -1;

	pakfire_package_set_conflicts(self->package, relationlist);
	pakfire_relationlist_free(relationlist);

	return 0;
}

static PyObject* Package_add_conflicts(PackageObject* self, PyObject* args) {
	RelationObject* relation = NULL;

	if (!PyArg_ParseTuple(args, "O!", &RelationType, &relation))
		return NULL;

	pakfire_package_add_conflicts(self->package, relation->relation);

	Py_RETURN_NONE;
}

static PyObject* Package_get_recommends(PackageObject* self) {
	PakfireRelationList relationlist = pakfire_package_get_recommends(self->package);

	PyObject* list = PyList_FromRelationList(self->pool, relationlist);
	pakfire_relationlist_free(relationlist);

	return list;
}

static int Package_set_recommends(PackageObject* self, PyObject* value) {
	PakfireRelationList relationlist = PyList_AsRelationList(self->pool, value);
	if (!relationlist)
		return -1;

	pakfire_package_set_recommends(self->package, relationlist);
	pakfire_relationlist_free(relationlist);

	return 0;
}

static PyObject* Package_add_recommends(PackageObject* self, PyObject* args) {
	RelationObject* relation = NULL;

	if (!PyArg_ParseTuple(args, "O!", &RelationType, &relation))
		return NULL;

	pakfire_package_add_recommends(self->package, relation->relation);

	Py_RETURN_NONE;
}

static PyObject* Package_get_suggests(PackageObject* self) {
	PakfireRelationList relationlist = pakfire_package_get_suggests(self->package);

	PyObject* list = PyList_FromRelationList(self->pool, relationlist);
	pakfire_relationlist_free(relationlist);

	return list;
}

static int Package_set_suggests(PackageObject* self, PyObject* value) {
	PakfireRelationList relationlist = PyList_AsRelationList(self->pool, value);
	if (!relationlist)
		return -1;

	pakfire_package_set_suggests(self->package, relationlist);
	pakfire_relationlist_free(relationlist);

	return 0;
}

static PyObject* Package_add_suggests(PackageObject* self, PyObject* args) {
	RelationObject* relation = NULL;

	if (!PyArg_ParseTuple(args, "O!", &RelationType, &relation))
		return NULL;

	pakfire_package_add_suggests(self->package, relation->relation);

	Py_RETURN_NONE;
}

static PyObject* Package_get_filelist(PackageObject* self, PyObject* args) {
	PyObject* list = PyList_New(0);
	if (list == NULL)
		return NULL;

	PakfireFile file = pakfire_package_get_filelist(self->package);
	while (file) {
		const char* name = pakfire_file_get_name(file);

		PyObject* obj = PyUnicode_FromString(name);

		int ret = PyList_Append(list, obj);
		Py_DECREF(obj);

		if (ret == -1)
			goto fail;

		file = pakfire_file_get_next(file);
	}

	return list;

fail:
	Py_DECREF(list);
	return NULL;
}

static int Package_set_filelist(PackageObject* self, PyObject* value) {
	if (!PySequence_Check(value)) {
		PyErr_SetString(PyExc_AttributeError, "Expected a sequence.");
		return -1;
	}

	PakfirePackage pkg = self->package;
	pakfire_package_filelist_remove(pkg);

	const int length = PySequence_Length(value);
	for (int i = 0; i < length; i++) {
		PyObject* item = PySequence_GetItem(value, i);

		if (!PyUnicode_Check(item)) {
			Py_DECREF(item);

			PyErr_SetString(PyExc_AttributeError, "Expected a string");
			return -1;
		}

		const char* name = PyUnicode_AsUTF8(item);

		PakfireFile file = pakfire_package_filelist_append(pkg, name);

# if 0
		PakfireFile file = pakfire_package_filelist_append(pkg);
		pakfire_file_set_name(file, name);
#endif

		Py_DECREF(item);
	}

	return 0;
}

static PyObject* Package_dump(PackageObject* self, PyObject *args, PyObject* kwds) {
	static char* kwlist[] = {"long", "filelist", NULL};

	int long_format = 0;
	int filelist = 0;

	if (!PyArg_ParseTupleAndKeywords(args, kwds, "|ii", kwlist, &long_format, &filelist))
		return NULL;

	int flags = 0;
	if (long_format)
		flags |= PAKFIRE_PKG_DUMP_LONG;

	if (filelist)
		flags |= PAKFIRE_PKG_DUMP_FILELIST;

	char* package_dump = pakfire_package_dump(self->package, flags);

	if (!package_dump)
		Py_RETURN_NONE;

	return PyUnicode_FromString(package_dump);
}

static struct PyMethodDef Package_methods[] = {
	{
		"add_provides",
		(PyCFunction)Package_add_provides,
		METH_VARARGS,
		NULL
	},
	{
		"add_requires",
		(PyCFunction)Package_add_requires,
		METH_VARARGS,
		NULL
	},
	{
		"add_conflicts",
		(PyCFunction)Package_add_conflicts,
		METH_VARARGS,
		NULL
	},
	{
		"add_obsoletes",
		(PyCFunction)Package_add_obsoletes,
		METH_VARARGS,
		NULL
	},
	{
		"add_recommends",
		(PyCFunction)Package_add_recommends,
		METH_VARARGS,
		NULL
	},
	{
		"add_suggests",
		(PyCFunction)Package_add_suggests,
		METH_VARARGS,
		NULL
	},
	{
		"dump",
		(PyCFunction)Package_dump,
		METH_VARARGS|METH_KEYWORDS,
		NULL
	},
	{ NULL },
};

static struct PyGetSetDef Package_getsetters[] = {
	{
		"name",
		(getter)Package_get_name,
		(setter)Package_set_name,
		NULL,
		NULL
	},
	{
		"epoch",
		(getter)Package_get_epoch,
		NULL,
		NULL,
		NULL
	},
	{
		"version",
		(getter)Package_get_version,
		NULL,
		NULL,
		NULL
	},
	{
		"release",
		(getter)Package_get_release,
		NULL,
		NULL,
		NULL
	},
	{
		"evr",
		(getter)Package_get_evr,
		NULL,
		NULL,
		NULL
	},
	{
		"arch",
		(getter)Package_get_arch,
		(setter)Package_set_arch,
		NULL,
		NULL
	},
	{
		"uuid",
		(getter)Package_get_uuid,
		(setter)Package_set_uuid,
		NULL,
		NULL
	},
	{
		"checksum",
		(getter)Package_get_checksum,
		(setter)Package_set_checksum,
		NULL,
		NULL
	},
	{
		"summary",
		(getter)Package_get_summary,
		(setter)Package_set_summary,
		NULL,
		NULL
	},
	{
		"description",
		(getter)Package_get_description,
		(setter)Package_set_description,
		NULL,
		NULL
	},
	{
		"license",
		(getter)Package_get_license,
		(setter)Package_set_license,
		NULL,
		NULL
	},
	{
		"url",
		(getter)Package_get_url,
		(setter)Package_set_url,
		NULL,
		NULL
	},
	{
		"groups",
		(getter)Package_get_groups,
		(setter)Package_set_groups,
		NULL,
		NULL
	},
	{
		"vendor",
		(getter)Package_get_vendor,
		(setter)Package_set_vendor,
		NULL,
		NULL
	},
	{
		"maintainer",
		(getter)Package_get_maintainer,
		(setter)Package_set_maintainer,
		NULL,
		NULL
	},
	{
		"filename",
		(getter)Package_get_filename,
		(setter)Package_set_filename,
		NULL,
		NULL
	},
	{
		"installed",
		(getter)Package_get_installed,
		NULL,
		NULL,
		NULL
	},
	{
		"downloadsize",
		(getter)Package_get_downloadsize,
		(setter)Package_set_downloadsize,
		NULL,
		NULL
	},
	{
		"installsize",
		(getter)Package_get_installsize,
		(setter)Package_set_installsize,
		NULL,
		NULL
	},
	{
		"size",
		(getter)Package_get_size,
		NULL,
		NULL,
		NULL
	},
	{
		"buildhost",
		(getter)Package_get_buildhost,
		(setter)Package_set_buildhost,
		NULL,
		NULL
	},
	{
		"buildtime",
		(getter)Package_get_buildtime,
		(setter)Package_set_buildtime,
		NULL,
		NULL
	},
	{
		"cache_path",
		(getter)Package_get_cache_path,
		NULL,
		NULL,
		NULL
	},
	{
		"cache_full_path",
		(getter)Package_get_cache_full_path,
		NULL,
		NULL,
		NULL
	},

	// Dependencies
	{
		"provides",
		(getter)Package_get_provides,
		(setter)Package_set_provides,
		NULL,
		NULL
	},
	{
		"requires",
		(getter)Package_get_requires,
		(setter)Package_set_requires,
		NULL,
		NULL
	},
	{
		"obsoletes",
		(getter)Package_get_obsoletes,
		(setter)Package_set_obsoletes,
		NULL,
		NULL
	},
	{
		"conflicts",
		(getter)Package_get_conflicts,
		(setter)Package_set_conflicts,
		NULL,
		NULL
	},
	{
		"recommends",
		(getter)Package_get_recommends,
		(setter)Package_set_recommends,
		NULL,
		NULL
	},
	{
		"suggests",
		(getter)Package_get_suggests,
		(setter)Package_set_suggests,
		NULL,
		NULL
	},

	// Repository
	{
		"repo",
		(getter)Package_get_repo,
		(setter)Package_set_repo,
		NULL,
		NULL
	},
	{
		"location",
		(getter)Package_get_location,
		NULL,
		NULL,
		NULL
	},

	// Filelist
	{
		"filelist",
		(getter)Package_get_filelist,
		(setter)Package_set_filelist,
		NULL,
		NULL
	},

	{ NULL }
};

PyTypeObject PackageType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	tp_name:            "_pakfire.Package",
	tp_basicsize:       sizeof(PackageObject),
	tp_flags:           Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
	tp_new:             Package_new,
	tp_dealloc:         (destructor)Package_dealloc,
	tp_init:            (initproc)Package_init,
	tp_doc:             "Package object",
	tp_methods:         Package_methods,
	tp_getset:          Package_getsetters,
	tp_hash:            (hashfunc)Package_hash,
	tp_repr:            (reprfunc)Package_repr,
	tp_str:             (reprfunc)Package_str,
	tp_richcompare:     (richcmpfunc)Package_richcompare,
};
