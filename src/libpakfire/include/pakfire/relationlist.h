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

#ifndef PAKFIRE_RELATIONLIST_H
#define PAKFIRE_RELATIONLIST_H

#include <pakfire/types.h>

PakfireRelationList pakfire_relationlist_create(Pakfire pakfire);
PakfireRelationList pakfire_relationlist_create_from_string(Pakfire pakfire, const char* s);

PakfireRelationList pakfire_relationlist_ref(PakfireRelationList relationlist);
PakfireRelationList pakfire_relationlist_unref(PakfireRelationList relationlist);

void pakfire_relationlist_add(PakfireRelationList relationlist, PakfireRelation relation);
int pakfire_relationlist_count(PakfireRelationList relationlist);

PakfireRelation pakfire_relationlist_get_clone(PakfireRelationList relationlist, int index);

#ifdef PAKFIRE_PRIVATE

PakfireRelationList pakfire_relationlist_from_queue(Pakfire pakfire, Queue q);
void pakfire_relationlist_clone_to_queue(PakfireRelationList relationlist, Queue* q);

#endif

#endif /* PAKFIRE_RELATIONLIST_H */
