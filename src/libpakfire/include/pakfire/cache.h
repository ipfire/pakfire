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

#ifndef PAKFIRE_CACHE_H
#define PAKFIRE_CACHE_H

#include <stdio.h>

#include <pakfire/types.h>

PakfireCache pakfire_cache_create(PakfirePool pool, const char* path);
void pakfire_cache_free(PakfireCache cache);

const char* pakfire_cache_get_path(PakfireCache cache);
char* pakfire_cache_get_full_path(PakfireCache cache, const char* path);

int pakfire_cache_has_file(PakfireCache cache, const char* filename);
char* pakfire_cache_get_package_path(PakfireCache cache, PakfirePackage pkg);
int pakfire_cache_has_package(PakfireCache cache, PakfirePackage pkg);
int pakfire_cache_age(PakfireCache cache, const char* filename);

FILE* pakfire_cache_open(PakfireCache cache, const char* filename, const char* flags);

#ifdef PAKFIRE_PRIVATE

struct _PakfireCache {
	PakfirePool pool;
	char* path;
};

#endif

#endif /* PAKFIRE_CACHE_H */
