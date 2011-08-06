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

#include "config.h"
#include "relation.h"
#include "repo.h"
#include "solvable.h"

PyTypeObject SolvableType = {
	PyObject_HEAD_INIT(NULL)
	tp_name: "_pakfire.Solvable",
	tp_basicsize: sizeof(SolvableObject),
	tp_flags: Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
	tp_new : Solvable_new,
	tp_dealloc: (destructor) Solvable_dealloc,
	tp_doc: "Sat Solvable objects",
	tp_str: (reprfunc)Solvable_string,
};

// Solvable
PyObject* Solvable_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
	SolvableObject *self;

	RepoObject *repo;
	const char *name;
	const char *evr;
	const char *arch = "noarch";

	if (!PyArg_ParseTuple(args, "Oss|s", &repo, &name, &evr, &arch)) {
		/* XXX raise exception */
		return NULL;
	}

	self = (SolvableObject *)type->tp_alloc(type, 0);
	if (self != NULL) {
		self->_id = repo_add_solvable(repo->_repo);
		self->_pool = repo->_repo->pool;

		/* Fill solvable with data. */
		Solvable *solv = pool_id2solvable(self->_pool, self->_id);

		solv->name = pool_str2id(self->_pool, name, 1);
		solv->evr = pool_str2id(self->_pool, evr, 1);
		solv->arch = pool_str2id(self->_pool, arch, 1);

		/* add self-provides */
		Id rel = pool_rel2id(self->_pool, solv->name, solv->evr, REL_EQ, 1);
		solv->provides = repo_addid_dep(repo->_repo, solv->provides, rel, 0);
	}

	return (PyObject *)self;
}

PyObject *Solvable_dealloc(SolvableObject *self) {
	self->ob_type->tp_free((PyObject *)self);

	Py_RETURN_NONE;
}

PyObject *Solvable_string(SolvableObject *self) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	const char *str = pool_solvable2str(self->_pool, solvable);

	return Py_BuildValue("s", str);
}

PyObject *Solvable_get_name(SolvableObject *self) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	const char *name = pool_id2str(solvable->repo->pool, solvable->name);

	return Py_BuildValue("s", name);
}

PyObject *Solvable_get_evr(SolvableObject *self) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	const char *evr = pool_id2str(solvable->repo->pool, solvable->evr);

	return Py_BuildValue("s", evr);
}

PyObject *Solvable_get_arch(SolvableObject *self) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	const char *arch = pool_id2str(solvable->repo->pool, solvable->arch);

	return Py_BuildValue("s", arch);
}

PyObject *Solvable_get_vendor(SolvableObject *self) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	const char *vendor = pool_id2str(solvable->repo->pool, solvable->vendor);

	return Py_BuildValue("s", vendor);
}

PyObject *Solvable_set_vendor(SolvableObject *self, PyObject *args) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	const char *vendor;
	if (!PyArg_ParseTuple(args, "s", &vendor)) {
		/* XXX raise exception */
		return NULL;
	}

	solvable->vendor = pool_str2id(self->_pool, vendor, 1);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_repo_name(SolvableObject *self) {
	Solvable *solvable = pool_id2solvable(self->_pool, self->_id);

	return Py_BuildValue("s", solvable->repo->name);
}

PyObject *Solvable_add_provides(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	RelationObject *rel;
	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
		return NULL;
	}

	solv->provides = repo_addid_dep(solv->repo, solv->provides, rel->_id, 0);

	Py_RETURN_NONE;
}

PyObject *_Solvable_get_dependencies(Solvable *solv, Offset deps) {
	Repo *repo = solv->repo;
	Pool *pool = repo->pool;

	Id id, *ids;
	const char *dep_str;

	PyObject *list = PyList_New(0);

	ids = repo->idarraydata + deps;
	while((id = *ids++) != 0) {
		dep_str = pool_dep2str(pool, id);

		// Do not include the filelist.
		if (strcmp(dep_str, "solvable:filemarker") == 0)
			break;

		PyList_Append(list, Py_BuildValue("s", dep_str));
	}

	Py_INCREF(list);
	return list;
}

PyObject *Solvable_get_provides(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	return _Solvable_get_dependencies(solv, solv->provides);
}

PyObject *Solvable_add_requires(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	RelationObject *rel;
	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
		return NULL;
	}

	solv->requires = repo_addid_dep(solv->repo, solv->requires, rel->_id, 0);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_requires(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	return _Solvable_get_dependencies(solv, solv->requires);
}

PyObject *Solvable_add_obsoletes(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	RelationObject *rel;
	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
		return NULL;
	}

	solv->obsoletes = repo_addid_dep(solv->repo, solv->obsoletes, rel->_id, 0);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_obsoletes(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	return _Solvable_get_dependencies(solv, solv->obsoletes);
}

PyObject *Solvable_add_conflicts(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	RelationObject *rel;
	if (!PyArg_ParseTuple(args, "O", &rel)) {
		/* XXX raise exception */
		return NULL;
	}

	solv->conflicts = repo_addid_dep(solv->repo, solv->conflicts, rel->_id, 0);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_conflicts(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	return _Solvable_get_dependencies(solv, solv->conflicts);
}

PyObject *Solvable_set_uuid(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *uuid;

	if (!PyArg_ParseTuple(args, "s", &uuid)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_PKGID, uuid);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_uuid(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *uuid = repo_lookup_str(solv->repo, self->_id, SOLVABLE_PKGID);

	return Py_BuildValue("s", uuid);
}

PyObject *Solvable_set_hash1(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *hash1;

	if (!PyArg_ParseTuple(args, "s", &hash1)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_CHECKSUM, hash1);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_hash1(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *hash1 = repo_lookup_str(solv->repo, self->_id, SOLVABLE_CHECKSUM);

	return Py_BuildValue("s", hash1);
}

PyObject *Solvable_set_summary(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *summary;

	if (!PyArg_ParseTuple(args, "s", &summary)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_SUMMARY, summary);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_summary(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *summary = repo_lookup_str(solv->repo, self->_id, SOLVABLE_SUMMARY);

	return Py_BuildValue("s", summary);
}

PyObject *Solvable_set_description(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *desc;

	if (!PyArg_ParseTuple(args, "s", &desc)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_DESCRIPTION, desc);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_description(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *desc = repo_lookup_str(solv->repo, self->_id,
		SOLVABLE_DESCRIPTION);

	return Py_BuildValue("s", desc);
}

PyObject *Solvable_set_url(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *url;

	if (!PyArg_ParseTuple(args, "s", &url)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_URL, url);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_url(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *url = repo_lookup_str(solv->repo, self->_id, SOLVABLE_URL);

	return Py_BuildValue("s", url);
}

PyObject *Solvable_set_groups(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *groups;

	if (!PyArg_ParseTuple(args, "s", &groups)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_GROUP, groups);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_groups(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *groups = repo_lookup_str(solv->repo, self->_id, SOLVABLE_GROUP);

	return Py_BuildValue("s", groups);
}

PyObject *Solvable_set_filename(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *filename;

	if (!PyArg_ParseTuple(args, "s", &filename)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_MEDIAFILE, filename);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_filename(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *filename = repo_lookup_str(solv->repo, self->_id,
		SOLVABLE_MEDIAFILE);

	return Py_BuildValue("s", filename);
}

PyObject *Solvable_set_license(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *license;

	if (!PyArg_ParseTuple(args, "s", &license)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_LICENSE, license);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_license(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *license = repo_lookup_str(solv->repo, self->_id,
		SOLVABLE_LICENSE);

	return Py_BuildValue("s", license);
}

PyObject *Solvable_set_buildhost(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *buildhost;

	if (!PyArg_ParseTuple(args, "s", &buildhost)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_BUILDHOST, buildhost);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_buildhost(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *buildhost = repo_lookup_str(solv->repo, self->_id,
		SOLVABLE_BUILDHOST);

	return Py_BuildValue("s", buildhost);
}

PyObject *Solvable_set_maintainer(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *maintainer;

	if (!PyArg_ParseTuple(args, "s", &maintainer)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_str(solv->repo, self->_id, SOLVABLE_PACKAGER, maintainer);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_maintainer(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	const char *maintainer = repo_lookup_str(solv->repo, self->_id,
		SOLVABLE_PACKAGER);

	return Py_BuildValue("s", maintainer);
}

PyObject *Solvable_set_downloadsize(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	unsigned int downloadsize;

	if (!PyArg_ParseTuple(args, "i", &downloadsize)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_num(solv->repo, self->_id, SOLVABLE_DOWNLOADSIZE, downloadsize);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_downloadsize(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	unsigned int downloadsize = repo_lookup_num(solv->repo, self->_id,
		SOLVABLE_DOWNLOADSIZE, 0);

	return Py_BuildValue("i", downloadsize);
}

PyObject *Solvable_set_installsize(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	unsigned int installedsize;

	if (!PyArg_ParseTuple(args, "i", &installedsize)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_num(solv->repo, self->_id, SOLVABLE_INSTALLSIZE, installedsize);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_installsize(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	unsigned int installedsize = repo_lookup_num(solv->repo, self->_id,
		SOLVABLE_INSTALLSIZE, 0);

	return Py_BuildValue("i", installedsize);
}

PyObject *Solvable_set_buildtime(SolvableObject *self, PyObject *args) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	unsigned int buildtime;

	if (!PyArg_ParseTuple(args, "i", &buildtime)) {
		/* XXX raise exception */
		return NULL;
	}

	repo_set_num(solv->repo, self->_id, SOLVABLE_BUILDTIME, buildtime);

	Py_RETURN_NONE;
}

PyObject *Solvable_get_buildtime(SolvableObject *self) {
	Solvable *solv = pool_id2solvable(self->_pool, self->_id);

	unsigned int buildtime = repo_lookup_num(solv->repo, self->_id,
		SOLVABLE_BUILDTIME, 0);

	if (buildtime == 0)
		Py_RETURN_NONE;

	return Py_BuildValue("i", buildtime);
}

