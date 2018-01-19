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

#define _XOPEN_SOURCE 500
#include <ftw.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

#include <pakfire/cache.h>
#include <pakfire/constants.h>
#include <pakfire/package.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/repocache.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

static char* pakfire_repocache_prefix(PakfireRepoCache repo_cache) {
	const char* repo_name = pakfire_repo_get_name(repo_cache->repo);

	char buffer[STRING_SIZE] = "";
	snprintf(buffer, sizeof(buffer), "repodata/%s", repo_name);

	return pakfire_strdup(buffer);
}

PAKFIRE_EXPORT PakfireRepoCache pakfire_repocache_create(PakfireRepo repo) {
	PakfireRepoCache repo_cache = pakfire_calloc(1, sizeof(*repo_cache));

	repo_cache->repo = repo;
	repo_cache->prefix = pakfire_repocache_prefix(repo_cache);

	return repo_cache;
}

PAKFIRE_EXPORT void pakfire_repocache_free(PakfireRepoCache repo_cache) {
	pakfire_free(repo_cache->prefix);
	pakfire_free(repo_cache);
}

PAKFIRE_EXPORT char* pakfire_repocache_get_cache_path(PakfireRepoCache repo_cache, const char* path) {
	return pakfire_path_join(repo_cache->prefix, path);
}

PAKFIRE_EXPORT char* pakfire_repocache_get_full_path(PakfireRepoCache repo_cache, const char* path) {
	char* cache_path = pakfire_repocache_get_cache_path(repo_cache, path);

	PakfireCache cache = pakfire_repocache_cache(repo_cache);
	char* full_path = pakfire_cache_get_full_path(cache, cache_path);

	pakfire_free(cache_path);

	return full_path;
}

PAKFIRE_EXPORT int pakfire_repocache_has_file(PakfireRepoCache repo_cache, const char* filename) {
	char* cache_filename = pakfire_repocache_get_cache_path(repo_cache, filename);

	PakfireCache cache = pakfire_repocache_cache(repo_cache);
	int r = pakfire_cache_access(cache, cache_filename, R_OK);

	pakfire_free(cache_filename);
	return r;
}

PAKFIRE_EXPORT int pakfire_repocache_age(PakfireRepoCache repo_cache, const char* filename) {
	char* cache_filename = pakfire_repocache_get_cache_path(repo_cache, filename);

	PakfireCache cache = pakfire_repocache_cache(repo_cache);
	int age = pakfire_cache_age(cache, cache_filename);
	pakfire_free(cache_filename);

	return age;
}

PAKFIRE_EXPORT FILE* pakfire_repocache_open(PakfireRepoCache repo_cache, const char* filename, const char* flags) {
	char* cache_filename = pakfire_repocache_get_cache_path(repo_cache, filename);

	PakfireCache cache = pakfire_repocache_cache(repo_cache);
	FILE* fp = pakfire_cache_open(cache, cache_filename, flags);
	pakfire_free(cache_filename);

	return fp;
}
