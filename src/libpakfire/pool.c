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

#include <solv/evr.h>
#include <solv/pool.h>
#include <solv/poolarch.h>
#include <solv/queue.h>
#include <solv/repo.h>

#include <pakfire/cache.h>
#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/pakfire.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

struct _PakfirePool {
	Pool* pool;
	int provides_ready;
	Queue installonly;

	PakfireCache cache;
	int nrefs;
};

PAKFIRE_EXPORT PakfirePool pakfire_pool_create(Pakfire pakfire) {
	PakfirePool pool = pakfire_calloc(1, sizeof(*pool));
	if (pool) {
		DEBUG("Allocated Pool at %p\n", pool);
		pool->nrefs = 1;

		// Initialize pool
		pool->pool = pool_create();
		queue_init(&pool->installonly);

		// Self-reference this object in libsolv
		pool->pool->appdata = pool;

		// Set architecture
		const char* arch = pakfire_get_arch(pakfire);
		pool_setarch(pool->pool, arch);
	}

	return pool;
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

static void pakfire_pool_free(PakfirePool pool) {
	pakfire_pool_free_repos(pool->pool);

	queue_free(&pool->installonly);

	pool_free(pool->pool);
	pakfire_free(pool);

	DEBUG("Released Pool at %p\n", pool);
}

PAKFIRE_EXPORT PakfirePool pakfire_pool_ref(PakfirePool pool) {
	++pool->nrefs;

	return pool;
}

PAKFIRE_EXPORT PakfirePool pakfire_pool_unref(PakfirePool pool) {
	if (!pool)
		return NULL;

	if (--pool->nrefs > 0)
		return pool;

	pakfire_pool_free(pool);
	return NULL;
}

Pool* pakfire_pool_get_solv_pool(PakfirePool pool) {
	return pool->pool;
}

PAKFIRE_EXPORT int pakfire_pool_version_compare(PakfirePool pool, const char* evr1, const char* evr2) {
	return pool_evrcmp_str(pool->pool, evr1, evr2, EVRCMP_COMPARE);
}

PAKFIRE_EXPORT int pakfire_pool_count(PakfirePool pool) {
	int cnt = 0;

	for (int i = 2; i < pool->pool->nsolvables; i++) {
		Solvable* s = pool->pool->solvables + i;
		if (s->repo)
			cnt++;
	}

	return cnt;
}

void pakfire_pool_has_changed(PakfirePool pool) {
	pool->provides_ready = 0;
}

void pakfire_pool_apply_changes(PakfirePool pool) {
	if (!pool->provides_ready) {
		pool_addfileprovides(pool->pool);
		pool_createwhatprovides(pool->pool);
		pool->provides_ready = 1;
	}
}

PAKFIRE_EXPORT const char** pakfire_pool_get_installonly(PakfirePool pool) {
	Queue q;
	queue_init_clone(&q, &pool->installonly);

	const char** installonly = pakfire_malloc(sizeof(const char*) * (q.count + 1));

	int i = 0;
	while (q.count) {
		installonly[i++] = pool_id2str(pool->pool, queue_shift(&q));
	}
	installonly[i] = NULL;

	queue_free(&q);

	return installonly;
}

Queue* pakfire_pool_get_installonly_queue(PakfirePool pool) {
	return &pool->installonly;
}

PAKFIRE_EXPORT void pakfire_pool_set_installonly(PakfirePool pool, const char** installonly) {
	queue_empty(&pool->installonly);

	if (installonly == NULL)
		return;

	const char* name;
	while ((name = *installonly++) != NULL)
		queue_pushunique(&pool->installonly, pool_str2id(pool->pool, name, 1));
}

PAKFIRE_EXPORT const char* pakfire_pool_get_cache_path(PakfirePool pool) {
	if (!pool->cache)
		return NULL;

	return pakfire_cache_get_path(pool->cache);
}

PAKFIRE_EXPORT void pakfire_pool_set_cache_path(PakfirePool pool, const char* path) {
	if (pool->cache)
		pakfire_cache_free(pool->cache);

	pool->cache = pakfire_cache_create(pool, path);
}

PAKFIRE_EXPORT PakfireCache pakfire_pool_get_cache(PakfirePool pool) {
	if (pool->cache)
		return pool->cache;

	return NULL;
}

static PakfirePackageList pakfire_pool_dataiterator(PakfirePool pool, const char* what, int key, int flags) {
	PakfirePackageList list = pakfire_packagelist_create();
	pakfire_pool_apply_changes(pool);

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
	dataiterator_init(&di, pool->pool, 0, 0, key, what, di_flags);
	while (dataiterator_step(&di)) {
		PakfirePackage pkg = pakfire_package_create(pool, di.solvid);
		pakfire_packagelist_push_if_not_exists(list, pkg);
	}
	dataiterator_free(&di);

	return list;
}

static PakfirePackageList pakfire_pool_search_name(PakfirePool _pool, const char* name, int flags) {
	if (!flags) {
		PakfirePackageList list = pakfire_packagelist_create();
		pakfire_pool_apply_changes(_pool);

		Pool* pool = _pool->pool;
		Id id = pool_str2id(pool, name, 0);
		if (id == 0)
			return list;

		Id p, pp;
		FOR_PROVIDES(p, pp, id) {
			Solvable* s = pool_id2solvable(pool, p);

			if (s->name == id) {
				PakfirePackage pkg = pakfire_package_create(_pool, p);
				pakfire_packagelist_push_if_not_exists(list, pkg);
			}
		}

		return list;
	}

	return pakfire_pool_dataiterator(_pool, name, SOLVABLE_NAME, flags);
}

static PakfirePackageList pakfire_pool_search_provides(PakfirePool _pool, const char* provides, int flags) {
	if (!flags) {
		PakfirePackageList list = pakfire_packagelist_create();
		pakfire_pool_apply_changes(_pool);

		Pool* pool = _pool->pool;
		Id id = pool_str2id(pool, provides, 0);
		if (id == 0)
			return list;

		Id p, pp;
		FOR_PROVIDES(p, pp, id) {
			PakfirePackage pkg = pakfire_package_create(_pool, p);
			pakfire_packagelist_push_if_not_exists(list, pkg);
		}

		return list;
	}

	return pakfire_pool_dataiterator(_pool, provides, SOLVABLE_PROVIDES, flags);
}

PAKFIRE_EXPORT PakfirePackageList pakfire_pool_whatprovides(PakfirePool pool, const char* what, int flags) {
	assert((flags & ~(PAKFIRE_ICASE|PAKFIRE_NAME_ONLY|PAKFIRE_GLOB)) == 0);

	if (flags & PAKFIRE_NAME_ONLY) {
		flags &= ~PAKFIRE_NAME_ONLY;

		return pakfire_pool_search_name(pool, what, flags);
	} else {
		return pakfire_pool_search_provides(pool, what, flags);
	}
}

PAKFIRE_EXPORT PakfirePackageList pakfire_pool_search(PakfirePool pool, const char* what, int flags) {
	return pakfire_pool_dataiterator(pool, what, 0, PAKFIRE_SUBSTRING);
}

PAKFIRE_EXPORT char* pakfire_pool_tmpdup(Pool* pool, const char* s) {
	char* dup = pool_alloctmpspace(pool, strlen(s) + 1);

	return strcpy(dup, s);
}
