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

#ifndef PAKFIRE_RELATION_H
#define PAKFIRE_RELATION_H

#include <solv/pool.h>
#include <solv/pooltypes.h>
#include <solv/queue.h>

#include <pakfire/pool.h>
#include <pakfire/types.h>

PakfireRelation pakfire_relation_create(PakfirePool pool, const char* name, int cmp_type, const char* evr);
PakfireRelation pakfire_relation_create_from_id(PakfirePool pool, Id id);
void pakfire_relation_free(PakfireRelation relation);

Id pakfire_relation_id(PakfireRelation relation);
char* pakfire_relation_str(PakfireRelation relation);

PakfirePackageList pakfire_relation_providers(PakfireRelation relation);

int pakfire_relation2queue(const PakfireRelation relation, Queue* queue, int solver_action);

#ifdef PAKFIRE_PRIVATE

struct _PakfireRelation {
	PakfirePool pool;
	Id id;
};

static inline PakfirePool pakfire_relation_pool(PakfireRelation relation) {
	return relation->pool;
}

static inline Pool* pakfire_relation_solv_pool(PakfireRelation relation) {
	return pakfire_relation_pool(relation)->pool;
}

#endif

#endif /* PAKFIRE_RELATION_H */
