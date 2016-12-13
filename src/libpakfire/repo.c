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

#include <string.h>

#include <solv/repo.h>
#include <solv/repo_solv.h>
#include <solv/repo_write.h>

#include <pakfire/constants.h>
#include <pakfire/errno.h>
#include <pakfire/package.h>
#include <pakfire/pool.h>
#include <pakfire/repo.h>
#include <pakfire/repocache.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

static Repo* get_repo_by_name(Pool* pool, const char* name) {
	Repo* repo;
	int i;

	FOR_REPOS(i, repo) {
		if (strcmp(repo->name, name) == 0)
			return repo;
	}

	return NULL;
}

static PakfireRepo get_pakfire_repo_by_name(PakfirePool pool, const char* name) {
	Repo* repo = get_repo_by_name(pool->pool, name);

	if (repo)
		return repo->appdata;

	return NULL;
}

PakfireRepo pakfire_repo_create(PakfirePool pool, const char* name) {
	PakfireRepo repo = get_pakfire_repo_by_name(pool, name);
	if (repo) {
		repo->nrefs++;
		return repo;
	}

	Repo* r = get_repo_by_name(pool->pool, name);
	if (!r)
		r = repo_create(pool->pool, name);

	return pakfire_repo_create_from_repo(pool, r);
}

PakfireRepo pakfire_repo_create_from_repo(PakfirePool pool, Repo* r) {
	PakfireRepo repo;

	if (r->appdata) {
		repo = r->appdata;
		repo->nrefs++;

	} else {
		repo = pakfire_calloc(1, sizeof(*repo));
		if (repo) {
			repo->pool = pool;

			repo->repo = r;
			repo->cache = pakfire_repocache_create(repo);
			repo->repo->appdata = repo;

			repo->filelist = repo_add_repodata(r, REPO_EXTEND_SOLVABLES|REPO_LOCALPOOL|REPO_NO_INTERNALIZE|REPO_NO_LOCATION);

			// Initialize reference counter
			repo->nrefs = 1;
		}
	}

	return repo;
}

void pakfire_repo_free(PakfireRepo repo) {
	if (--repo->nrefs > 0)
		return;

	if (repo->repo)
		repo->repo->appdata = NULL;

	// Free repodata.
	repodata_free(repo->filelist);

	pakfire_free(repo);

	if (repo->cache)
		pakfire_repocache_free(repo->cache);
}

PakfirePool pakfire_repo_pool(PakfireRepo repo) {
	return repo->pool;
}

int pakfire_repo_identical(PakfireRepo repo1, PakfireRepo repo2) {
	Repo* r1 = repo1->repo;
	Repo* r2 = repo2->repo;

	return strcmp(r1->name, r2->name);
}

int pakfire_repo_cmp(PakfireRepo repo1, PakfireRepo repo2) {
	Repo* r1 = repo1->repo;
	Repo* r2 = repo2->repo;

	if (r1->priority > r2->priority)
		return 1;

	else if (r1->priority < r2->priority)
		return -1;

	return strcmp(r1->name, r2->name);
}

int pakfire_repo_count(PakfireRepo repo) {
	Pool* pool = pakfire_repo_solv_pool(repo);
	int cnt = 0;

	for (int i = 2; i < pool->nsolvables; i++) {
		Solvable* s = pool->solvables + i;
		if (s->repo && s->repo == repo->repo)
			cnt++;
	}

	return cnt;
}

void pakfire_repo_internalize(PakfireRepo repo) {
	repo_internalize(repo->repo);
}

const char* pakfire_repo_get_name(PakfireRepo repo) {
	return repo->repo->name;
}

void pakfire_repo_set_name(PakfireRepo repo, const char* name) {
	repo->repo->name = pakfire_strdup(name);
}

int pakfire_repo_get_enabled(PakfireRepo repo) {
	return !repo->repo->disabled;
}

void pakfire_repo_set_enabled(PakfireRepo repo, int enabled) {
	repo->repo->disabled = !enabled;

	PakfirePool pool = pakfire_repo_pool(repo);
	pool->provides_ready = 0;
}

int pakfire_repo_get_priority(PakfireRepo repo) {
	return repo->repo->priority;
}

void pakfire_repo_set_priority(PakfireRepo repo, int priority) {
	repo->repo->priority = priority;
}

int pakfire_repo_is_installed_repo(PakfireRepo repo) {
	PakfirePool pool = pakfire_repo_pool(repo);

	PakfireRepo installed_repo = pakfire_pool_get_installed_repo(pool);

	return pakfire_repo_identical(repo, installed_repo);
}

int pakfire_repo_read_solv(PakfireRepo repo, const char* filename, int flags) {
	FILE* f = fopen(filename, "rb");
	if (!f) {
		return PAKFIRE_E_IO;
	}

	int ret = pakfire_repo_read_solv_fp(repo, f, flags);
	fclose(f);

	return ret;
}

int pakfire_repo_read_solv_fp(PakfireRepo repo, FILE *f, int flags) {
	int ret = repo_add_solv(repo->repo, f, flags);

	repo->pool->provides_ready = 0;

	return ret;
}

int pakfire_repo_write_solv(PakfireRepo repo, const char* filename, int flags) {
	FILE* f = fopen(filename, "wb");
	if (!f) {
		return PAKFIRE_E_IO;
	}

	int ret = pakfire_repo_write_solv_fp(repo, f, flags);
	fclose(f);

	return ret;
}

int pakfire_repo_write_solv_fp(PakfireRepo repo, FILE *f, int flags) {
	pakfire_repo_internalize(repo);

	return repo_write(repo->repo, f);
}

PakfirePackage pakfire_repo_add_package(PakfireRepo repo) {
	Id id = repo_add_solvable(repo->repo);

	return pakfire_package_create(repo->pool, id);
}

PakfireRepoCache pakfire_repo_get_cache(PakfireRepo repo) {
	return repo->cache;
}
