/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2017 Pakfire development team                                 #
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

#ifndef PAKFIRE_PAKFIRE_H
#define PAKFIRE_PAKFIRE_H

#include <pakfire/types.h>

int pakfire_init();

Pakfire pakfire_create(const char* path, const char* arch);

Pakfire pakfire_ref(Pakfire pakfire);
Pakfire pakfire_unref(Pakfire pakfire);

const char* pakfire_get_path(Pakfire pakfire);
const char* pakfire_get_arch(Pakfire pakfire);

PakfirePool pakfire_get_pool(Pakfire pakfire);

const char** pakfire_get_installonly(Pakfire pakfire);
void pakfire_set_installonly(Pakfire pakfire, const char** installonly);

int pakfire_version_compare(Pakfire pakfire, const char* evr1, const char* evr2);

PakfireRepo pakfire_get_installed_repo(Pakfire pakfire);
void pakfire_set_installed_repo(Pakfire pakfire, PakfireRepo repo);

PakfirePackageList pakfire_whatprovides(Pakfire pakfire, const char* provides, int flags);
PakfirePackageList pakfire_search(Pakfire pakfire, const char* what, int flags);

#ifdef PAKFIRE_PRIVATE

#include <solv/pool.h>

void pakfire_pool_has_changed(Pakfire pakfire);
void pakfire_pool_apply_changes(Pakfire pakfire);

Pool* pakfire_get_solv_pool(Pakfire pakfire);
Queue* pakfire_get_installonly_queue(Pakfire pakfire);

#endif

#endif /* PAKFIRE_PAKFIRE_H */
