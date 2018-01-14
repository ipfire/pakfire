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

#ifndef PAKFIRE_PACKAGELIST_H
#define PAKFIRE_PACKAGELIST_H

#include <solv/queue.h>

#include <pakfire/types.h>

PakfirePackageList pakfire_packagelist_create(void);
PakfirePackageList pakfire_packagelist_ref(PakfirePackageList list);
PakfirePackageList pakfire_packagelist_unref(PakfirePackageList list);

size_t pakfire_packagelist_count(PakfirePackageList list);
void pakfire_packagelist_sort(PakfirePackageList list);
int pakfire_packagelist_has(PakfirePackageList list, PakfirePackage pkg);
PakfirePackage pakfire_packagelist_get(PakfirePackageList list, unsigned int index);

void pakfire_packagelist_push(PakfirePackageList list, PakfirePackage pkg);
void pakfire_packagelist_push_if_not_exists(PakfirePackageList list, PakfirePackage pkg);

#ifdef PAKFIRE_PRIVATE

PakfirePackageList pakfire_packagelist_from_queue(PakfirePool _pool, Queue* q);

#endif

#endif /* PAKFIRE_PACKAGELIST_H */
