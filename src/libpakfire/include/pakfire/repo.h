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

#ifndef PAKFIRE_REPO_H
#define PAKFIRE_REPO_H

#include <solv/repo.h>

#include <pakfire/types.h>

PakfireRepo pakfire_repo_create(PakfirePool pool, const char* name);
PakfireRepo pakfire_repo_create_from_repo(PakfirePool pool, Repo* r);
void pakfire_repo_free(PakfireRepo pkg);

PakfirePool pakfire_repo_pool(PakfireRepo repo);

int pakfire_repo_identical(PakfireRepo repo1, PakfireRepo repo2);
int pakfire_repo_cmp(PakfireRepo repo1, PakfireRepo repo2);
int pakfire_repo_count(PakfireRepo repo);

void pakfire_repo_internalize(PakfireRepo repo);

const char* pakfire_repo_get_name(PakfireRepo repo);
void pakfire_repo_set_name(PakfireRepo repo, const char* name);

int pakfire_repo_get_enabled(PakfireRepo repo);
void pakfire_repo_set_enabled(PakfireRepo repo, int enabled);

int pakfire_repo_get_priority(PakfireRepo repo);
void pakfire_repo_set_priority(PakfireRepo repo, int priority);

int pakfire_repo_is_installed_repo(PakfireRepo repo);

int pakfire_repo_read_solv(PakfireRepo repo, const char* filename, int flags);
int pakfire_repo_read_solv_fp(PakfireRepo repo, FILE *f, int flags);

int pakfire_repo_write_solv(PakfireRepo repo, const char* filename, int flags);
int pakfire_repo_write_solv_fp(PakfireRepo repo, FILE *f, int flags);

PakfireRepoCache pakfire_repo_get_cache(PakfireRepo repo);

int pakfire_repo_clean(PakfireRepo repo);

#ifdef PAKFIRE_PRIVATE

struct _PakfireRepo {
	PakfirePool pool;
	Repo* repo;
	PakfireRepoCache cache;
	int nrefs;

	Repodata* filelist;
};

PakfirePackage pakfire_repo_add_package(PakfireRepo repo);

static inline Pool* pakfire_repo_solv_pool(PakfireRepo repo) {
	return pakfire_pool_get_solv_pool(repo->pool);
}

static inline Repo* pakfire_repo_get_solv_repo(PakfireRepo repo) {
	return repo->repo;
}

#endif

#endif /* PAKFIRE_REPO_H */
