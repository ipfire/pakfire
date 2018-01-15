/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2013 Pakfire development team                                 #
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

#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <solv/evr.h>
#include <solv/pool.h>
#include <solv/pooltypes.h>
#include <solv/repo.h>
#include <solv/solvable.h>

#include <pakfire/cache.h>
#include <pakfire/constants.h>
#include <pakfire/file.h>
#include <pakfire/i18n.h>
#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/packagecache.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/relation.h>
#include <pakfire/relationlist.h>
#include <pakfire/repo.h>
#include <pakfire/repocache.h>
#include <pakfire/util.h>

struct _PakfirePackage {
	PakfirePool pool;
	Id id;
	PakfireFile filelist;
	int nrefs;
};

static Pool* pakfire_package_get_solv_pool(PakfirePackage pkg) {
    return pakfire_pool_get_solv_pool(pkg->pool);
}

static void pakfire_package_add_self_provides(PakfirePool pool, PakfirePackage pkg, const char* name, const char* evr) {
	PakfireRelation relation = pakfire_relation_create(pool, name, PAKFIRE_EQ, evr);
	pakfire_package_add_provides(pkg, relation);

	pakfire_relation_free(relation);
}

PAKFIRE_EXPORT PakfirePackage pakfire_package_create(PakfirePool pool, Id id) {
	PakfirePackage pkg = pakfire_calloc(1, sizeof(*pkg));
	if (pkg) {
		DEBUG("Allocated Package at %p\n", pkg);

		pkg->pool = pakfire_pool_ref(pool);
		pkg->id = id;

		// Initialize reference counter
		pkg->nrefs = 1;
	}

	return pkg;
}

PAKFIRE_EXPORT PakfirePackage pakfire_package_create2(PakfirePool pool, PakfireRepo repo, const char* name, const char* evr, const char* arch) {
	PakfirePackage pkg = pakfire_repo_add_package(repo);

	pakfire_package_set_name(pkg, name);
	pakfire_package_set_evr(pkg, evr);
	pakfire_package_set_arch(pkg, arch);

	pakfire_package_add_self_provides(pool, pkg, name, evr);

	return pkg;
}

static void pakfire_package_free(PakfirePackage pkg) {
	pakfire_pool_unref(pkg->pool);
	pakfire_package_filelist_remove(pkg);
	pakfire_free(pkg);

	DEBUG("Released Package at %p\n", pkg);
}

PAKFIRE_EXPORT PakfirePackage pakfire_package_ref(PakfirePackage pkg) {
	pkg->nrefs++;

	return pkg;
}

PAKFIRE_EXPORT PakfirePackage pakfire_package_unref(PakfirePackage pkg) {
	if (!pkg)
		return NULL;

	if (--pkg->nrefs > 0)
		return pkg;

	pakfire_package_free(pkg);
	return NULL;
}

static Solvable* get_solvable(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);

	return pool_id2solvable(pool, pkg->id);
}

static Repo* pakfire_package_solv_repo(PakfirePackage pkg) {
	Solvable* s = get_solvable(pkg);

	return s->repo;
}

static Id pakfire_package_get_handle(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	return s - pool->solvables;
}

PAKFIRE_EXPORT int pakfire_package_identical(PakfirePackage pkg1, PakfirePackage pkg2) {
	return pkg1->id == pkg2->id;
}

PAKFIRE_EXPORT int pakfire_package_cmp(PakfirePackage pkg1, PakfirePackage pkg2) {
	Pool* pool = pakfire_package_get_solv_pool(pkg1);

	Solvable* s1 = get_solvable(pkg1);
	Solvable* s2 = get_solvable(pkg2);

	// Check names
	const char* str1 = pool_id2str(pool, s1->name);
	const char* str2 = pool_id2str(pool, s2->name);

	int ret = strcmp(str1, str2);
	if (ret)
		return ret;

	// Check the version string
	ret = pakfire_package_evr_cmp(pkg1, pkg2);
	if (ret)
		return ret;

	// Check repositories
	PakfireRepo repo1 = pakfire_package_get_repo(pkg1);
	PakfireRepo repo2 = pakfire_package_get_repo(pkg2);

	if (repo1 && repo2) {
		ret = pakfire_repo_cmp(repo1, repo2);
	}

	pakfire_repo_unref(repo1);
	pakfire_repo_unref(repo2);

	if (ret)
		return ret;

	// Check package architectures
	str1 = pool_id2str(pool, s1->arch);
	str2 = pool_id2str(pool, s2->arch);

	return strcmp(str1, str2);
}

PAKFIRE_EXPORT int pakfire_package_evr_cmp(PakfirePackage pkg1, PakfirePackage pkg2) {
	Pool* pool = pakfire_package_get_solv_pool(pkg1);

	Solvable* s1 = get_solvable(pkg1);
	Solvable* s2 = get_solvable(pkg2);

	return pool_evrcmp(pool, s1->evr, s2->evr, EVRCMP_COMPARE);
}

PAKFIRE_EXPORT Id pakfire_package_id(PakfirePackage pkg) {
	return pkg->id;
}

PAKFIRE_EXPORT char* pakfire_package_get_nevra(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	const char* nevra = pool_solvable2str(pool, s);

	return pakfire_strdup(nevra);
}

PAKFIRE_EXPORT const char* pakfire_package_get_name(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	return pool_id2str(pool, s->name);
}

PAKFIRE_EXPORT void pakfire_package_set_name(PakfirePackage pkg, const char* name) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	s->name = pool_str2id(pool, name, 1);
}

PAKFIRE_EXPORT const char* pakfire_package_get_evr(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	return pool_id2str(pool, s->evr);
}

PAKFIRE_EXPORT void pakfire_package_set_evr(PakfirePackage pkg, const char* evr) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	s->evr = pool_str2id(pool, evr, 1);
}

static void split_evr(Pool* pool, const char* evr_c, char** epoch, char** version, char** release) {
    char* evr = pakfire_pool_tmpdup(pool, evr_c);
    char *e, *v, *r;

    for (e = evr + 1; *e != ':' && *e != '-'; ++e)
    	;

    if (*e == '-') {
		*e = '\0';
		v = evr;
		r = e + 1;
		e = NULL;
	} else { /* *e == ':' */
		*e = '\0';
		v = e + 1;
		e = evr;
		for (r = v + 1; *r != '-'; ++r)
			;
		*r = '\0';
		r++;
	}

    *epoch = e;
    *version = v;
    *release = r;
}

PAKFIRE_EXPORT unsigned long pakfire_package_get_epoch(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	char *e, *v, *r, *endptr;

    unsigned long epoch = 0;

	split_evr(pool, pakfire_package_get_evr(pkg), &e, &v, &r);

	if (e) {
		long int converted = strtol(e, &endptr, 10);
		assert(converted > 0);
		assert(*endptr == '\0');
		epoch = converted;
	}

	return epoch;
}

PAKFIRE_EXPORT const char* pakfire_package_get_version(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	char *e, *v, *r;

	split_evr(pool, pakfire_package_get_evr(pkg), &e, &v, &r);
	return pakfire_strdup(v);
}

PAKFIRE_EXPORT const char* pakfire_package_get_release(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	char *e, *v, *r;

	split_evr(pool, pakfire_package_get_evr(pkg), &e, &v, &r);
	return pakfire_strdup(r);
}

PAKFIRE_EXPORT const char* pakfire_package_get_arch(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	return pool_id2str(pool, s->arch);
}

PAKFIRE_EXPORT void pakfire_package_set_arch(PakfirePackage pkg, const char* arch) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	s->arch = pool_str2id(pool, arch, 1);
}

static void pakfire_package_internalize_repo(PakfirePackage pkg) {
	PakfireRepo repo = pakfire_package_get_repo(pkg);
	if (repo) {
		pakfire_repo_internalize(repo);
		pakfire_repo_unref(repo);
	}
}

static const char* pakfire_package_get_string(PakfirePackage pkg, int key) {
	pakfire_package_internalize_repo(pkg);

	Solvable* s = get_solvable(pkg);
	const char* str = solvable_lookup_str(s, key);

	if (!str)
		return NULL;

	if (strlen(str) == 0)
		return NULL;

	return str;
}

static void pakfire_package_set_string(PakfirePackage pkg, int key, const char* value) {
	Solvable* s = get_solvable(pkg);

	if (!value)
		value = "";

	solvable_set_str(s, key, value);
}

PAKFIRE_EXPORT const char* pakfire_package_get_uuid(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_PKGID);
}

PAKFIRE_EXPORT void pakfire_package_set_uuid(PakfirePackage pkg, const char* uuid) {
	pakfire_package_set_string(pkg, SOLVABLE_PKGID, uuid);
}

PAKFIRE_EXPORT const char* pakfire_package_get_checksum(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_CHECKSUM);
}

PAKFIRE_EXPORT void pakfire_package_set_checksum(PakfirePackage pkg, const char* checksum) {
	pakfire_package_set_string(pkg, SOLVABLE_CHECKSUM, checksum);
}

PAKFIRE_EXPORT const char* pakfire_package_get_summary(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_SUMMARY);
}

PAKFIRE_EXPORT void pakfire_package_set_summary(PakfirePackage pkg, const char* summary) {
	pakfire_package_set_string(pkg, SOLVABLE_SUMMARY, summary);
}

PAKFIRE_EXPORT const char* pakfire_package_get_description(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_DESCRIPTION);
}

PAKFIRE_EXPORT void pakfire_package_set_description(PakfirePackage pkg, const char* description) {
	pakfire_package_set_string(pkg, SOLVABLE_DESCRIPTION, description);
}

PAKFIRE_EXPORT const char* pakfire_package_get_license(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_LICENSE);
}

PAKFIRE_EXPORT void pakfire_package_set_license(PakfirePackage pkg, const char* license) {
	pakfire_package_set_string(pkg, SOLVABLE_LICENSE, license);
}

PAKFIRE_EXPORT const char* pakfire_package_get_url(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_URL);
}

PAKFIRE_EXPORT void pakfire_package_set_url(PakfirePackage pkg, const char* url) {
	pakfire_package_set_string(pkg, SOLVABLE_URL, url);
}

#warning the groups functions need to be refactored

PAKFIRE_EXPORT const char** pakfire_package_get_groups(PakfirePackage pkg) {
	const char* groups = pakfire_package_get_string(pkg, SOLVABLE_GROUP);

	const char** grouplist = NULL;
	char* group = strtok((char *)groups, " ");

	int i = 0;
	while (group != NULL) {
		grouplist = realloc(grouplist, sizeof(char *) * ++i);
		assert(grouplist);
		grouplist[i - 1] = group;

		group = strtok(NULL, " ");
	}
	grouplist[i] = NULL;

	return grouplist;
}

PAKFIRE_EXPORT void pakfire_package_set_groups(PakfirePackage pkg, const char** grouplist) {
	char groups[2048] = "";

	if (grouplist) {
		const char* group;
		while ((group = *grouplist++) != NULL) {
			if (groups[0])
				strcat(groups, " ");

			strcat(groups, group);
		}
		groups[sizeof(groups) - 1] = '\0';
	} else
		groups[0] = '\0';

	pakfire_package_set_string(pkg, SOLVABLE_GROUP, (const char *)&groups);
}

PAKFIRE_EXPORT const char* pakfire_package_get_vendor(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_VENDOR);
}

PAKFIRE_EXPORT void pakfire_package_set_vendor(PakfirePackage pkg, const char* vendor) {
	pakfire_package_set_string(pkg, SOLVABLE_VENDOR, vendor);
}

PAKFIRE_EXPORT const char* pakfire_package_get_maintainer(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_PACKAGER);
}

PAKFIRE_EXPORT void pakfire_package_set_maintainer(PakfirePackage pkg, const char* maintainer) {
	pakfire_package_set_string(pkg, SOLVABLE_PACKAGER, maintainer);
}

PAKFIRE_EXPORT const char* pakfire_package_get_filename(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_MEDIAFILE);
}

PAKFIRE_EXPORT void pakfire_package_set_filename(PakfirePackage pkg, const char* filename) {
	pakfire_package_set_string(pkg, SOLVABLE_MEDIAFILE, filename);
}

PAKFIRE_EXPORT int pakfire_package_is_installed(PakfirePackage pkg) {
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Solvable* s = get_solvable(pkg);

	return pool->installed == s->repo;
}

static unsigned long long pakfire_package_get_num(PakfirePackage pkg, Id type) {
	pakfire_package_internalize_repo(pkg);

	Solvable* s = get_solvable(pkg);
	return solvable_lookup_num(s, type, 0);
}

static void pakfire_package_set_num(PakfirePackage pkg, Id type, unsigned long long value) {
	Solvable* s = get_solvable(pkg);

	solvable_set_num(s, type, value);
}

PAKFIRE_EXPORT unsigned long long pakfire_package_get_downloadsize(PakfirePackage pkg) {
	return pakfire_package_get_num(pkg, SOLVABLE_DOWNLOADSIZE);
}

PAKFIRE_EXPORT void pakfire_package_set_downloadsize(PakfirePackage pkg, unsigned long long downloadsize) {
	return pakfire_package_set_num(pkg, SOLVABLE_DOWNLOADSIZE, downloadsize);
}

PAKFIRE_EXPORT unsigned long long pakfire_package_get_installsize(PakfirePackage pkg) {
	return pakfire_package_get_num(pkg, SOLVABLE_INSTALLSIZE);
}

PAKFIRE_EXPORT void pakfire_package_set_installsize(PakfirePackage pkg, unsigned long long installsize) {
	return pakfire_package_set_num(pkg, SOLVABLE_INSTALLSIZE, installsize);
}

PAKFIRE_EXPORT unsigned long long pakfire_package_get_size(PakfirePackage pkg) {
	if (pakfire_package_is_installed(pkg))
		return pakfire_package_get_installsize(pkg);

	return pakfire_package_get_downloadsize(pkg);
}

PAKFIRE_EXPORT const char* pakfire_package_get_buildhost(PakfirePackage pkg) {
	return pakfire_package_get_string(pkg, SOLVABLE_BUILDHOST);
}

PAKFIRE_EXPORT void pakfire_package_set_buildhost(PakfirePackage pkg, const char* buildhost) {
	pakfire_package_set_string(pkg, SOLVABLE_BUILDHOST, buildhost);
}

PAKFIRE_EXPORT unsigned long long pakfire_package_get_buildtime(PakfirePackage pkg) {
	return pakfire_package_get_num(pkg, SOLVABLE_BUILDTIME);
}

PAKFIRE_EXPORT void pakfire_package_set_buildtime(PakfirePackage pkg, unsigned long long buildtime) {
	pakfire_package_set_num(pkg, SOLVABLE_BUILDTIME, buildtime);
}

PAKFIRE_EXPORT unsigned long long pakfire_package_get_installtime(PakfirePackage pkg) {
	return pakfire_package_get_num(pkg, SOLVABLE_INSTALLTIME);
}

static PakfireRelationList pakfire_package_get_relationlist(PakfirePackage pkg, Id type) {
	Queue q;
	queue_init(&q);

	Solvable* s = get_solvable(pkg);
	solvable_lookup_idarray(s, type, &q);

	PakfireRelationList relationlist = pakfire_relationlist_from_queue(pkg->pool, q);

	queue_free(&q);

	return relationlist;
}

static void pakfire_package_set_relationlist(PakfirePackage pkg, Id type, PakfireRelationList relationlist) {
#if 0
	// This implemention should be the fastest, but unfortunately does not work.
	Queue q;
	pakfire_relationlist_clone_to_queue(relationlist, &q);

	Solvable* s = get_solvable(pkg);
	solvable_set_idarray(s, type, &q);

	queue_free(&q);
#endif

	Solvable* s = get_solvable(pkg);
	solvable_unset(s, type);

	int count = pakfire_relationlist_count(relationlist);
	for (int i = 0; i < count; i++) {
		PakfireRelation relation = pakfire_relationlist_get_clone(relationlist, i);
		solvable_add_idarray(s, type, relation->id);

		pakfire_relation_free(relation);
	}
}

static void pakfire_package_add_relation(PakfirePackage pkg, Id type, PakfireRelation relation) {
	Solvable* s = get_solvable(pkg);

	solvable_add_idarray(s, type, relation->id);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_provides(PakfirePackage pkg) {
	return pakfire_package_get_relationlist(pkg, SOLVABLE_PROVIDES);
}

PAKFIRE_EXPORT void pakfire_package_set_provides(PakfirePackage pkg, PakfireRelationList relationlist) {
	pakfire_package_set_relationlist(pkg, SOLVABLE_PROVIDES, relationlist);
}

PAKFIRE_EXPORT void pakfire_package_add_provides(PakfirePackage pkg, PakfireRelation relation) {
	pakfire_package_add_relation(pkg, SOLVABLE_PROVIDES, relation);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_prerequires(PakfirePackage pkg) {
	#warning TODO
	return NULL;
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_requires(PakfirePackage pkg) {
	return pakfire_package_get_relationlist(pkg, SOLVABLE_REQUIRES);
}

PAKFIRE_EXPORT void pakfire_package_set_requires(PakfirePackage pkg, PakfireRelationList relationlist) {
	pakfire_package_set_relationlist(pkg, SOLVABLE_REQUIRES, relationlist);
}

PAKFIRE_EXPORT void pakfire_package_add_requires(PakfirePackage pkg, PakfireRelation relation) {
	pakfire_package_add_relation(pkg, SOLVABLE_REQUIRES, relation);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_conflicts(PakfirePackage pkg) {
	return pakfire_package_get_relationlist(pkg, SOLVABLE_CONFLICTS);
}

PAKFIRE_EXPORT void pakfire_package_set_conflicts(PakfirePackage pkg, PakfireRelationList relationlist) {
	pakfire_package_set_relationlist(pkg, SOLVABLE_CONFLICTS, relationlist);
}

PAKFIRE_EXPORT void pakfire_package_add_conflicts(PakfirePackage pkg, PakfireRelation relation) {
	pakfire_package_add_relation(pkg, SOLVABLE_CONFLICTS, relation);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_obsoletes(PakfirePackage pkg) {
	return pakfire_package_get_relationlist(pkg, SOLVABLE_OBSOLETES);
}

PAKFIRE_EXPORT void pakfire_package_set_obsoletes(PakfirePackage pkg, PakfireRelationList relationlist) {
	pakfire_package_set_relationlist(pkg, SOLVABLE_OBSOLETES, relationlist);
}

PAKFIRE_EXPORT void pakfire_package_add_obsoletes(PakfirePackage pkg, PakfireRelation relation) {
	pakfire_package_add_relation(pkg, SOLVABLE_OBSOLETES, relation);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_recommends(PakfirePackage pkg) {
	return pakfire_package_get_relationlist(pkg, SOLVABLE_RECOMMENDS);
}

PAKFIRE_EXPORT void pakfire_package_set_recommends(PakfirePackage pkg, PakfireRelationList relationlist) {
	pakfire_package_set_relationlist(pkg, SOLVABLE_RECOMMENDS, relationlist);
}

PAKFIRE_EXPORT void pakfire_package_add_recommends(PakfirePackage pkg, PakfireRelation relation) {
	pakfire_package_add_relation(pkg, SOLVABLE_RECOMMENDS, relation);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_package_get_suggests(PakfirePackage pkg) {
	return pakfire_package_get_relationlist(pkg, SOLVABLE_SUGGESTS);
}

PAKFIRE_EXPORT void pakfire_package_set_suggests(PakfirePackage pkg, PakfireRelationList relationlist) {
	pakfire_package_set_relationlist(pkg, SOLVABLE_SUGGESTS, relationlist);
}

PAKFIRE_EXPORT void pakfire_package_add_suggests(PakfirePackage pkg, PakfireRelation relation) {
	pakfire_package_add_relation(pkg, SOLVABLE_SUGGESTS, relation);
}

PAKFIRE_EXPORT PakfireRepo pakfire_package_get_repo(PakfirePackage pkg) {
	Solvable* s = get_solvable(pkg);

	return pakfire_repo_create_from_repo(pkg->pool, s->repo);
}

PAKFIRE_EXPORT void pakfire_package_set_repo(PakfirePackage pkg, PakfireRepo repo) {
	Solvable* s = get_solvable(pkg);

	s->repo = pakfire_repo_get_repo(repo);
}

PAKFIRE_EXPORT char* pakfire_package_get_location(PakfirePackage pkg) {
	pakfire_package_internalize_repo(pkg);

	Solvable* s = get_solvable(pkg);

	const char* location = solvable_get_location(s, NULL);
	return pakfire_strdup(location);
}

static void pakfire_package_dump_add_line(char** str, const char* key, const char* val) {
	if (val)
		asprintf(str, "%s%-15s: %s\n", *str, key ? key : "", val);
}

static void pakfire_package_dump_add_lines(char** str, const char* key, const char* val) {
	const char* string = val;

	while (*string) {
		char line[STRING_SIZE];
		int counter = 0;

		while (*string) {
			if (*string == '\n') {
				string++;
				break;
			}

			line[counter++] = *string++;
		}
		line[counter] = '\0';

		if (*line) {
			pakfire_package_dump_add_line(str, key, line);
			key = NULL;
		}
	}
}

static void pakfire_package_dump_add_line_date(char** str, const char* key, unsigned long long date) {
	// Convert from integer to tm struct.
	struct tm* timer = gmtime((time_t *)&date);

	char val[STRING_SIZE];
	strftime(val, STRING_SIZE, "%a, %d %b %Y %T %z", timer);

	pakfire_package_dump_add_line(str, key, val);
}

static void pakfire_package_dump_add_line_relations(char** str, const char* key, PakfireRelationList deps) {
	int count = pakfire_relationlist_count(deps);
	for (int i = 0; i < count; i++) {
		PakfireRelation relation = pakfire_relationlist_get_clone(deps, i);

		if (relation) {
			char* dep = pakfire_relation_str(relation);
			pakfire_relation_free(relation);

			// Stop here and don't list any files.
			if (strcmp(PAKFIRE_SOLVABLE_FILEMARKER, dep) == 0)
				break;

			if (dep) {
				pakfire_package_dump_add_line(str, (i == 0) ? key : "", dep);
				pakfire_free(dep);
			}
		}
	}
}

static void pakfire_package_dump_add_line_size(char** str, const char* key, unsigned long long size) {
	char* val = pakfire_format_size(size);

	if (val) {
		pakfire_package_dump_add_line(str, key, val);
		pakfire_free(val);
	}
}

PAKFIRE_EXPORT char* pakfire_package_dump(PakfirePackage pkg, int flags) {
	char* string = "";

	// Name
	const char* name = pakfire_package_get_name(pkg);
	pakfire_package_dump_add_line(&string, _("Name"), name);

	// Version
	const char* version = pakfire_package_get_version(pkg);
	pakfire_package_dump_add_line(&string, _("Version"), version);

	// Release
	const char* release = pakfire_package_get_release(pkg);
	pakfire_package_dump_add_line(&string, _("Release"), release);

	// Size
	unsigned long long size = pakfire_package_get_size(pkg);
	pakfire_package_dump_add_line_size(&string, _("Size"), size);

	// Installed size
	if (pakfire_package_is_installed(pkg)) {
		unsigned long long installsize = pakfire_package_get_installsize(pkg);
		pakfire_package_dump_add_line_size(&string, _("Installed size"), installsize);

	// Downloadsize
	} else {
		unsigned long long downloadsize = pakfire_package_get_downloadsize(pkg);
		pakfire_package_dump_add_line_size(&string, _("Download size"), downloadsize);
	}

	PakfireRepo repo = pakfire_package_get_repo(pkg);
	if (repo) {
		const char* repo_name = pakfire_repo_get_name(repo);
		pakfire_package_dump_add_line(&string, _("Repo"), repo_name);

		pakfire_repo_unref(repo);
	}

	// Summary
	const char* summary = pakfire_package_get_summary(pkg);
	pakfire_package_dump_add_line(&string, _("Summary"), summary);

	// Description
	const char* description = pakfire_package_get_description(pkg);
	pakfire_package_dump_add_lines(&string, _("Description"), description);

	// Groups
	#warning TODO groups

	// URL
	const char* url = pakfire_package_get_url(pkg);
	pakfire_package_dump_add_line(&string, _("URL"), url);

	// License
	const char* license = pakfire_package_get_license(pkg);
	pakfire_package_dump_add_line(&string, _("License"), license);

	if (flags & PAKFIRE_PKG_DUMP_LONG) {
		// Maintainer
		const char* maintainer = pakfire_package_get_maintainer(pkg);
		pakfire_package_dump_add_line(&string, _("Maintainer"), maintainer);

		// Vendor
		const char* vendor = pakfire_package_get_vendor(pkg);
		pakfire_package_dump_add_line(&string, _("Vendor"), vendor);

		// UUID
		const char* uuid = pakfire_package_get_uuid(pkg);
		pakfire_package_dump_add_line(&string, _("UUID"), uuid);

		// Build time
		unsigned long long buildtime = pakfire_package_get_buildtime(pkg);
		pakfire_package_dump_add_line_date(&string, _("Build date"), buildtime);

		// Build host
		const char* buildhost = pakfire_package_get_buildhost(pkg);
		pakfire_package_dump_add_line(&string, _("Build host"), buildhost);

		PakfireRelationList provides = pakfire_package_get_provides(pkg);
		if (provides) {
			pakfire_package_dump_add_line_relations(&string, _("Provides"), provides);
			pakfire_relationlist_free(provides);
		}

		PakfireRelationList requires = pakfire_package_get_requires(pkg);
		if (requires) {
			pakfire_package_dump_add_line_relations(&string, _("Requires"), requires);
			pakfire_relationlist_free(requires);
		}

		PakfireRelationList conflicts = pakfire_package_get_conflicts(pkg);
		if (conflicts) {
			pakfire_package_dump_add_line_relations(&string, _("Conflicts"), conflicts);
			pakfire_relationlist_free(conflicts);
		}

		PakfireRelationList obsoletes = pakfire_package_get_obsoletes(pkg);
		if (obsoletes) {
			pakfire_package_dump_add_line_relations(&string, _("Obsoletes"), obsoletes);
			pakfire_relationlist_free(obsoletes);
		}

		PakfireRelationList recommends = pakfire_package_get_recommends(pkg);
		if (recommends) {
			pakfire_package_dump_add_line_relations(&string, _("Recommends"), recommends);
			pakfire_relationlist_free(recommends);
		}

		PakfireRelationList suggests = pakfire_package_get_suggests(pkg);
		if (suggests) {
			pakfire_package_dump_add_line_relations(&string, _("Suggests"), suggests);
			pakfire_relationlist_free(suggests);
		}
	}

	if (flags & PAKFIRE_PKG_DUMP_FILELIST) {
		PakfireFile file = pakfire_package_get_filelist(pkg);

		char* prefix = _("Filelist");
		while (file) {
			const char* name = pakfire_file_get_name(file);
			pakfire_package_dump_add_line(&string, prefix, name);

			file = pakfire_file_get_next(file);

			// Only prefix the first line.
			prefix = NULL;
		}
	}

	return string;
}

PAKFIRE_EXPORT int pakfire_package_is_cached(PakfirePackage pkg) {
	PakfireCache cache = pakfire_pool_get_cache(pkg->pool);
	if (!cache)
		return 1;

	return pakfire_cache_has_package(cache, pkg);
}

PAKFIRE_EXPORT char* pakfire_package_get_cache_path(PakfirePackage pkg) {
	PakfireCache cache = pakfire_pool_get_cache(pkg->pool);
	if (!cache)
		return NULL;

	return pakfire_cache_get_package_path(cache, pkg);
}

PAKFIRE_EXPORT char* pakfire_package_get_cache_full_path(PakfirePackage pkg) {
	char* cache_path = NULL;

	char* pkg_cache_path = pakfire_package_get_cache_path(pkg);
	if (!pkg_cache_path)
		return NULL;

	PakfireRepo repo = pakfire_package_get_repo(pkg);
	if (!repo)
		goto out;

	PakfireRepoCache repo_cache = pakfire_repo_get_cache(repo);
	if (!repo_cache) {
		goto out;
	}

	cache_path = pakfire_repocache_get_full_path(repo_cache, pkg_cache_path);

out:
	pakfire_repo_unref(repo);

	return cache_path;
}

static PakfireFile pakfire_package_fetch_legacy_filelist(PakfirePackage pkg) {
	pakfire_package_internalize_repo(pkg);

	PakfireFile file = NULL;
	PakfireRepo repo = pakfire_package_get_repo(pkg);
	Solvable* s = get_solvable(pkg);
	Pool* p = pakfire_package_get_solv_pool(pkg);
	Repo* r = pakfire_repo_get_repo(repo);

	int found_marker = 0;

	Id id, *ids;
	ids = r->idarraydata + s->provides;
	while((id = *ids++) != 0) {
		const char* filename = pool_dep2str(p, id);

		if (found_marker) {
			if (file) {
				file = pakfire_file_append(file);
			} else {
				file = pakfire_file_create();
			}

			pakfire_file_set_name(file, filename);
			continue;
		}

		if (strcmp(filename, PAKFIRE_SOLVABLE_FILEMARKER) == 0)
			++found_marker;
	}

	if (file) {
		file = pakfire_file_get_first(file);

		// Sort the output
		file = pakfire_file_sort(file);
	}

	pakfire_repo_unref(repo);

	return file;
}

static PakfireFile pakfire_package_fetch_filelist(PakfirePackage pkg) {
	pakfire_package_internalize_repo(pkg);

	PakfireFile file = NULL;
	Pool* pool = pakfire_package_get_solv_pool(pkg);
	Repo* repo = pakfire_package_solv_repo(pkg);
	Id handle = pakfire_package_get_handle(pkg);

	Dataiterator di;
	dataiterator_init(&di, pool, repo, handle,
		SOLVABLE_FILELIST, NULL, SEARCH_FILES | SEARCH_COMPLETE_FILELIST);
	while (dataiterator_step(&di)) {
		if (file) {
			file = pakfire_file_append(file);
		} else {
			file = pakfire_file_create();
		}

		pakfire_file_set_name(file, di.kv.str);
	}
	dataiterator_free(&di);

	if (file) {
		file = pakfire_file_get_first(file);

		// Sort the result.
		file = pakfire_file_sort(file);
	}

	// If the file list is empty, we fall back to read files
	// in the older format.
	if (!file)
		file = pakfire_package_fetch_legacy_filelist(pkg);

	return file;
}

PAKFIRE_EXPORT PakfireFile pakfire_package_get_filelist(PakfirePackage pkg) {
	if (!pkg->filelist) {
		pkg->filelist = pakfire_package_fetch_filelist(pkg);
	}

	return pkg->filelist;
}

PAKFIRE_EXPORT PakfireFile pakfire_package_filelist_append(PakfirePackage pkg, const char* filename) {
	PakfireRepo repo = pakfire_package_get_repo(pkg);
	Repodata* repodata = pakfire_repo_get_repodata(repo);

	Id handle = pakfire_package_get_handle(pkg);

	char* dirname  = pakfire_dirname(filename);
	char* basename = pakfire_basename(filename);

	Id did = repodata_str2dir(repodata, dirname, 1);
	if (!did)
		did = repodata_str2dir(repodata, "/", 1);

	repodata_add_dirstr(repodata, handle,
		SOLVABLE_FILELIST, did, basename);

	pakfire_repo_unref(repo);

	return NULL;
}

#if 0
PakfireFile pakfire_package_filelist_append(PakfirePackage pkg) {
	if (pkg->filelist) {
		return pakfire_file_append(pkg->filelist);
	}

	PakfireFile file = pakfire_file_create();
	pkg->filelist = file;

	return file;
}
#endif

PAKFIRE_EXPORT void pakfire_package_filelist_remove(PakfirePackage pkg) {
	if (pkg->filelist)
		pakfire_file_free_all(pkg->filelist);
}
