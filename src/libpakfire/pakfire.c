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

#include <solv/evr.h>
#include <solv/pool.h>
#include <solv/poolarch.h>
#include <solv/queue.h>

#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/pakfire.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/system.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

struct _Pakfire {
	char* path;
	char* arch;

	// Pool stuff
	PakfirePool _pool;
	Pool* pool;
	int pool_ready;
	Queue installonly;

	// Logging
	pakfire_log_function_t log_function;
	int log_priority;

	// Cache
	PakfireCache cache;

	int nrefs;
};

PAKFIRE_EXPORT int pakfire_init() {
	// Setup logging
	pakfire_setup_logging();

	return 0;
}

PAKFIRE_EXPORT Pakfire pakfire_create(const char* path, const char* arch) {
	Pakfire pakfire = pakfire_calloc(1, sizeof(*pakfire));
	if (pakfire) {
		pakfire->nrefs = 1;

		pakfire->path = pakfire_strdup(path);
		if (!arch)
			arch = system_machine();
		pakfire->arch = pakfire_strdup(arch);

		DEBUG("Pakfire initialized at %p\n", pakfire);
		DEBUG("  arch = %s\n", pakfire_get_arch(pakfire));
		DEBUG("  path = %s\n", pakfire_get_path(pakfire));

		// Initialize the pool
		pakfire->_pool = pakfire_pool_create(pakfire);
		pakfire->pool = pool_create();

		// Set architecture of the pool
		pool_setarch(pakfire->pool, pakfire->arch);
	}

	return pakfire;
}

PAKFIRE_EXPORT Pakfire pakfire_ref(Pakfire pakfire) {
	++pakfire->nrefs;

	return pakfire;
}

static void pakfire_pool_free_repos(Pool* pool) {
	Repo* repo;
	int i;

	FOR_REPOS(i, repo) {
		PakfireRepo r = repo->appdata;
		if (r == NULL)
			continue;

		pakfire_repo_unref(r);
	}
}

PAKFIRE_EXPORT Pakfire pakfire_unref(Pakfire pakfire) {
	if (!pakfire)
		return NULL;

	if (--pakfire->nrefs > 0)
		return pakfire;

	pakfire_pool_unref(pakfire->_pool);
	pakfire_pool_free_repos(pakfire->pool);
	pool_free(pakfire->pool);
	queue_free(&pakfire->installonly);

	pakfire_free(pakfire->path);
	pakfire_free(pakfire->arch);

	pakfire_free(pakfire);

	DEBUG("Pakfire released at %p\n", pakfire);

	return NULL;
}

PAKFIRE_EXPORT const char* pakfire_get_path(Pakfire pakfire) {
	return pakfire->path;
}

PAKFIRE_EXPORT const char* pakfire_get_arch(Pakfire pakfire) {
	return pakfire->arch;
}

PAKFIRE_EXPORT PakfirePool pakfire_get_pool(Pakfire pakfire) {
	return pakfire_pool_ref(pakfire->_pool);
}

PAKFIRE_EXPORT int pakfire_version_compare(Pakfire pakfire, const char* evr1, const char* evr2) {
	return pool_evrcmp_str(pakfire->pool, evr1, evr2, EVRCMP_COMPARE);
}

Pool* pakfire_get_solv_pool(Pakfire pakfire) {
	return pakfire->pool;
}

void pakfire_pool_has_changed(Pakfire pakfire) {
	pakfire->pool_ready = 0;
}

void pakfire_pool_apply_changes(Pakfire pakfire) {
	if (!pakfire->pool_ready) {
		pool_addfileprovides(pakfire->pool);
		pool_createwhatprovides(pakfire->pool);
		pakfire->pool_ready = 1;
	}
}

PAKFIRE_EXPORT PakfireRepo pakfire_get_installed_repo(Pakfire pakfire) {
	if (!pakfire->pool->installed)
		return NULL;

	return pakfire_repo_create_from_repo(pakfire, pakfire->pool->installed);
}

PAKFIRE_EXPORT void pakfire_set_installed_repo(Pakfire pakfire, PakfireRepo repo) {
	if (!repo) {
		pool_set_installed(pakfire->pool, NULL);
		return;
	}

	pool_set_installed(pakfire->pool, pakfire_repo_get_repo(repo));
}

PAKFIRE_EXPORT const char** pakfire_get_installonly(Pakfire pakfire) {
	Queue q;
	queue_init_clone(&q, &pakfire->installonly);

	const char** installonly = pakfire_malloc(sizeof(const char*) * (q.count + 1));

	int i = 0;
	while (q.count) {
		installonly[i++] = pool_id2str(pakfire->pool, queue_shift(&q));
	}
	installonly[i] = NULL;

	queue_free(&q);

	return installonly;
}

Queue* pakfire_get_installonly_queue(Pakfire pakfire) {
	return &pakfire->installonly;
}

PAKFIRE_EXPORT void pakfire_set_installonly(Pakfire pakfire, const char** installonly) {
	queue_empty(&pakfire->installonly);

	if (installonly == NULL)
		return;

	const char* name;
	while ((name = *installonly++) != NULL)
		queue_pushunique(&pakfire->installonly, pool_str2id(pakfire->pool, name, 1));
}

static PakfirePackageList pakfire_pool_dataiterator(Pakfire pakfire, const char* what, int key, int flags) {
	PakfirePackageList list = pakfire_packagelist_create();
	pakfire_pool_apply_changes(pakfire);

	int di_flags = 0;
	if (flags & PAKFIRE_SUBSTRING)
		di_flags |= SEARCH_SUBSTRING;
	else
		di_flags |= SEARCH_STRING;

	if (flags & PAKFIRE_ICASE)
		di_flags |= SEARCH_NOCASE;
	if (flags & PAKFIRE_GLOB)
		di_flags |= SEARCH_GLOB;

	Dataiterator di;
	dataiterator_init(&di, pakfire->pool, 0, 0, key, what, di_flags);
	while (dataiterator_step(&di)) {
		PakfirePackage pkg = pakfire_package_create(pakfire, di.solvid);
		pakfire_packagelist_push_if_not_exists(list, pkg);
	}
	dataiterator_free(&di);

	return list;
}

static PakfirePackageList pakfire_search_name(Pakfire pakfire, const char* name, int flags) {
	if (!flags) {
		PakfirePackageList list = pakfire_packagelist_create();
		pakfire_pool_apply_changes(pakfire);

		Id id = pool_str2id(pakfire->pool, name, 0);
		if (id == 0)
			return list;

		Id p, pp;
		Pool* pool = pakfire->pool;
		FOR_PROVIDES(p, pp, id) {
			Solvable* s = pool_id2solvable(pakfire->pool, p);

			if (s->name == id) {
				PakfirePackage pkg = pakfire_package_create(pakfire, p);
				pakfire_packagelist_push_if_not_exists(list, pkg);
			}
		}

		return list;
	}

	return pakfire_pool_dataiterator(pakfire, name, SOLVABLE_NAME, flags);
}

static PakfirePackageList pakfire_search_provides(Pakfire pakfire, const char* provides, int flags) {
	if (!flags) {
		PakfirePackageList list = pakfire_packagelist_create();
		pakfire_pool_apply_changes(pakfire);

		Id id = pool_str2id(pakfire->pool, provides, 0);
		if (id == 0)
			return list;

		Id p, pp;
		Pool* pool = pakfire->pool;
		FOR_PROVIDES(p, pp, id) {
			PakfirePackage pkg = pakfire_package_create(pakfire, p);
			pakfire_packagelist_push_if_not_exists(list, pkg);
		}

		return list;
	}

	return pakfire_pool_dataiterator(pakfire, provides, SOLVABLE_PROVIDES, flags);
}

PAKFIRE_EXPORT PakfirePackageList pakfire_whatprovides(Pakfire pakfire, const char* what, int flags) {
	if (flags & PAKFIRE_NAME_ONLY) {
		flags &= ~PAKFIRE_NAME_ONLY;

		return pakfire_search_name(pakfire, what, flags);
	} else {
		return pakfire_search_provides(pakfire, what, flags);
	}
}

PAKFIRE_EXPORT PakfirePackageList pakfire_search(Pakfire pakfire, const char* what, int flags) {
	return pakfire_pool_dataiterator(pakfire, what, 0, PAKFIRE_SUBSTRING);
}
