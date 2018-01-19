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
#include <errno.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>

#include <pakfire/cache.h>
#include <pakfire/constants.h>
#include <pakfire/package.h>
#include <pakfire/private.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PAKFIRE_EXPORT PakfireCache pakfire_cache_create(PakfirePool pool, const char* path) {
	PakfireCache cache = pakfire_calloc(1, sizeof(*cache));

	cache->pool = pool;
	cache->path = pakfire_strdup(path);

	return cache;
}

PAKFIRE_EXPORT void pakfire_cache_free(PakfireCache cache) {
	pakfire_free(cache->path);
	pakfire_free(cache);
}

PAKFIRE_EXPORT const char* pakfire_cache_get_path(PakfireCache cache) {
	return cache->path;
}

PAKFIRE_EXPORT char* pakfire_cache_get_full_path(PakfireCache cache, const char* path) {
	const char* cache_path = pakfire_cache_get_path(cache);

	return pakfire_path_join(cache_path, path);
}
