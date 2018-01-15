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

PakfireRepo pakfire_get_installed_repo(Pakfire pakfire);
void pakfire_set_installed_repo(Pakfire pakfire, PakfireRepo repo);

#ifdef PAKFIRE_PRIVATE

#include <solv/pool.h>

Pool* pakfire_get_solv_pool(Pakfire pakfire);

#endif

#endif /* PAKFIRE_PAKFIRE_H */
