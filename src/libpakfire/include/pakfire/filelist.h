/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2014 Pakfire development team                                 #
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

#ifndef PAKFIRE_FILELIST_H
#define PAKFIRE_FILELIST_H

#include <pakfire/types.h>

int pakfire_filelist_create(PakfireFilelist* list);

PakfireFilelist pakfire_filelist_ref(PakfireFilelist list);
PakfireFilelist pakfire_filelist_unref(PakfireFilelist list);

size_t pakfire_filelist_size(PakfireFilelist list);
void pakfire_filelist_clear(PakfireFilelist list);

PakfireFile pakfire_filelist_get(PakfireFilelist list, size_t index);
int pakfire_filelist_append(PakfireFilelist list, PakfireFile file);

#endif /* PAKFIRE_FILELIST_H */
