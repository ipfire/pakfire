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

#ifndef PAKFIRE_POOL_H
#define PAKFIRE_POOL_H

#include <pakfire/types.h>

PakfirePool pakfire_pool_create(Pakfire pakfire);

PakfirePool pakfire_pool_ref(PakfirePool pool);
PakfirePool pakfire_pool_unref(PakfirePool pool);

const char* pakfire_pool_get_cache_path(PakfirePool pool);
void pakfire_pool_set_cache_path(PakfirePool pool, const char* path);
PakfireCache pakfire_pool_get_cache(PakfirePool pool);

PakfirePackageList pakfire_pool_whatprovides(PakfirePool pool, const char* provides, int flags);
PakfirePackageList pakfire_pool_search(PakfirePool pool, const char* what, int flags);

#ifdef PAKFIRE_PRIVATE

#include <solv/pool.h>

Pool* pakfire_pool_get_solv_pool(PakfirePool pool);
char* pakfire_pool_tmpdup(Pool* pool, const char* s);

#endif

#endif /* PAKFIRE_POOL_H */
