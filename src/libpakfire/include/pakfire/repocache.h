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

#ifndef PAKFIRE_REPOCACHE_H
#define PAKFIRE_REPOCACHE_H

#include <stdio.h>

#include <pakfire/types.h>

PakfireRepoCache pakfire_repocache_create(PakfireRepo repo);
void pakfire_repocache_free(PakfireRepoCache repo_cache);

char* pakfire_repocache_get_cache_path(PakfireRepoCache repo_cache, const char* path);
char* pakfire_repocache_get_full_path(PakfireRepoCache repo_cache, const char* path);

int pakfire_repocache_has_file(PakfireRepoCache repo_cache, const char* filename);
int pakfire_repocache_age(PakfireRepoCache repo_cache, const char* filename);

FILE* pakfire_repocache_open(PakfireRepoCache repo_cache, const char* filename, const char* flags);

int pakfire_repocache_destroy(PakfireRepoCache repo_cache);

#ifdef PAKFIRE_PRIVATE

struct _PakfireRepoCache {
	PakfireRepo repo;
	char* prefix;
};

inline PakfirePool pakfire_repocache_pool(PakfireRepoCache repo_cache) {
	return pakfire_repo_pool(repo_cache->repo);
}

inline PakfireCache pakfire_repocache_cache(PakfireRepoCache repo_cache) {
	PakfirePool pool = pakfire_repocache_pool(repo_cache);

	return pakfire_pool_get_cache(pool);
}

#endif

#endif /* PAKFIRE_REPOCACHE_H */
