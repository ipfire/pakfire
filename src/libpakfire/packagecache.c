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

#include <sys/stat.h>

#include <pakfire/constants.h>
#include <pakfire/package.h>
#include <pakfire/packagecache.h>
#include <pakfire/private.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PAKFIRE_EXPORT PakfirePackageCache pakfire_packagecache_create(PakfirePool pool, const char* path) {
	PakfirePackageCache cache = pakfire_calloc(1, sizeof(*cache));

	cache->pool = pool;
	cache->path = pakfire_strdup(path);

	return cache;
}

PAKFIRE_EXPORT void pakfire_packagecache_free(PakfirePackageCache cache) {
	pakfire_free(cache->path);
	pakfire_free(cache);
}

PAKFIRE_EXPORT const char* pakfire_packagecache_get_path(PakfirePackageCache cache) {
	return cache->path;
}

PAKFIRE_EXPORT char* pakfire_packagecache_get_package_path(PakfirePackageCache cache, PakfirePackage pkg) {
	char buffer[STRING_SIZE] = "";

	const char* filename = pakfire_package_get_filename(pkg);
	const char* checksum = pakfire_package_get_checksum(pkg);

	if (strlen(checksum) < 3)
		return NULL;

	snprintf(buffer, sizeof(buffer), "%s/%c%c/%s/%s", cache->path,
		checksum[0], checksum[1], checksum + 2, filename);

	return pakfire_strdup(buffer);
}

PAKFIRE_EXPORT int pakfire_packagecache_has_package(PakfirePackageCache cache, PakfirePackage pkg) {
	char* filename = pakfire_packagecache_get_package_path(cache, pkg);

	// Check if stat() is successful.
	struct stat buf;
	int r = stat(filename, &buf);

	pakfire_free(filename);
	return (r == 0);
}
