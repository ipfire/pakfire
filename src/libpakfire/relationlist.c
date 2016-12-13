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

#include <solv/pooltypes.h>
#include <solv/queue.h>

#include <pakfire/pool.h>
#include <pakfire/relation.h>
#include <pakfire/relationlist.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PakfireRelationList pakfire_relationlist_create(PakfirePool pool) {
	PakfireRelationList relationlist = pakfire_calloc(1, sizeof(*relationlist));
	if (relationlist) {
		relationlist->pool = pool;
		queue_init(&relationlist->queue);
	}

	return relationlist;
}

void pakfire_relationlist_free(PakfireRelationList relationlist) {
	queue_free(&relationlist->queue);
	pakfire_free(relationlist);
}

void pakfire_relationlist_add(PakfireRelationList relationlist, PakfireRelation relation) {
	queue_push(&relationlist->queue, relation->id);
}

int pakfire_relationlist_count(PakfireRelationList relationlist) {
	return relationlist->queue.count;
}

PakfireRelationList pakfire_relationlist_from_queue(PakfirePool pool, Queue q) {
	PakfireRelationList relationlist = pakfire_calloc(1, sizeof(*relationlist));
	if (relationlist) {
		relationlist->pool = pool;
		queue_init_clone(&relationlist->queue, &q);
	}

	return relationlist;
}

PakfireRelation pakfire_relationlist_get_clone(PakfireRelationList relationlist, int index) {
	Id id = relationlist->queue.elements[index];

	return pakfire_relation_create_from_id(relationlist->pool, id);
}

void pakfire_relationlist_clone_to_queue(PakfireRelationList relationlist, Queue* q) {
	queue_init_clone(q, &relationlist->queue);
}
