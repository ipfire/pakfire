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
#include <libgen.h>
#include <stdio.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include <pakfire/cache.h>
#include <pakfire/constants.h>
#include <pakfire/package.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PakfireCache pakfire_cache_create(PakfirePool pool, const char* path) {
	PakfireCache cache = pakfire_calloc(1, sizeof(*cache));

	cache->pool = pool;
	cache->path = pakfire_strdup(path);

	return cache;
}

void pakfire_cache_free(PakfireCache cache) {
	pakfire_free(cache->path);
	pakfire_free(cache);
}

const char* pakfire_cache_get_path(PakfireCache cache) {
	return cache->path;
}

char* pakfire_cache_get_full_path(PakfireCache cache, const char* path) {
	const char* cache_path = pakfire_cache_get_path(cache);

	return pakfire_path_join(cache_path, path);
}

static int pakfire_cache_stat(PakfireCache cache, const char* filename, struct stat* buf) {
	char* cache_filename = pakfire_cache_get_full_path(cache, filename);

	int r = stat(cache_filename, buf);
	pakfire_free(cache_filename);

	return r;
}

int pakfire_cache_has_file(PakfireCache cache, const char* filename) {
	struct stat buf;
	int r = pakfire_cache_stat(cache, filename, &buf);

	// Just check if stat() was sucessful.
	return (r == 0);
}

char* pakfire_cache_get_package_path(PakfireCache cache, PakfirePackage pkg) {
	char buffer[STRING_SIZE] = "";

	const char* filename = pakfire_package_get_filename(pkg);
	const char* checksum = pakfire_package_get_checksum(pkg);

	if (strlen(checksum) < 3)
		return NULL;

	snprintf(buffer, sizeof(buffer), "%c%c/%s/%s", checksum[0], checksum[1],
		checksum + 2, filename);

	return pakfire_strdup(buffer);
}

int pakfire_cache_has_package(PakfireCache cache, PakfirePackage pkg) {
	char* filename = pakfire_cache_get_package_path(cache, pkg);

	int r = pakfire_cache_has_file(cache, filename);
	pakfire_free(filename);

	return r;
}

int pakfire_cache_age(PakfireCache cache, const char* filename) {
	struct stat buf;
	int r = pakfire_cache_stat(cache, filename, &buf);

	if (r == 0) {
		// Get timestamp.
		time_t now = time(NULL);

		// Calculate the difference since the file has been created and now.
		time_t age = now - buf.st_ctime;

		return (int)age;
	}

	return -1;
}

static int pakfire_cache_mkdir(PakfireCache cache, const char* path, mode_t mode) {
	int r = 0;

	if ((strcmp(path, "/") == 0) || (strcmp(path, ".") == 0)) {
		return 0;
	}

	// If parent does not exists, we try to create it.
	char* parent_path = pakfire_dirname(path);
	r = access(parent_path, F_OK);
	if (r) {
		r = pakfire_cache_mkdir(cache, parent_path, mode);
	}
	pakfire_free(parent_path);

	if (!r) {
		// Finally, create the directory we want.
		r = mkdir(path, mode);

		if (r) {
			switch (errno) {
				// If the directory already exists, this is fine.
				case EEXIST:
					r = 0;
					break;
			}
		}
	}

	return r;
}

FILE* pakfire_cache_open(PakfireCache cache, const char* filename, const char* flags) {
	assert(filename);

	char* cache_filename = pakfire_cache_get_full_path(cache, filename);

	char* cache_dirname = pakfire_dirname(cache_filename);
	pakfire_cache_mkdir(cache, cache_dirname, S_IRUSR|S_IWUSR|S_IXUSR);

	FILE* fp = fopen(cache_filename, flags);

	pakfire_free(cache_filename);
	pakfire_free(cache_dirname);

	return fp;
}
