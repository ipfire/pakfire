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

#include <pakfire/logging.h>
#include <pakfire/pakfire.h>
#include <pakfire/private.h>
#include <pakfire/relation.h>
#include <pakfire/relationlist.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

struct _PakfireRelationList {
	Pakfire pakfire;
	Queue queue;
	int nrefs;
};

PAKFIRE_EXPORT PakfireRelationList pakfire_relationlist_create(Pakfire pakfire) {
	PakfireRelationList relationlist = pakfire_calloc(1, sizeof(*relationlist));
	if (relationlist) {
		DEBUG(pakfire, "Allocated RelationList at %p\n", relationlist);
		relationlist->nrefs = 1;

		relationlist->pakfire = pakfire_ref(pakfire);
		queue_init(&relationlist->queue);
	}

	return relationlist;
}

PAKFIRE_EXPORT PakfireRelationList pakfire_relationlist_ref(PakfireRelationList relationlist) {
	relationlist->nrefs++;

	return relationlist;
}

static void pakfire_relationlist_free(PakfireRelationList relationlist) {
	DEBUG(relationlist->pakfire, "Releasing RelationList at %p\n", relationlist);
	pakfire_unref(relationlist->pakfire);

	queue_free(&relationlist->queue);
	pakfire_free(relationlist);
}

PAKFIRE_EXPORT PakfireRelationList pakfire_relationlist_unref(PakfireRelationList relationlist) {
	if (!relationlist)
		return NULL;

	if (--relationlist->nrefs > 0)
		return relationlist;

	pakfire_relationlist_free(relationlist);
	return NULL;
}

PAKFIRE_EXPORT void pakfire_relationlist_add(PakfireRelationList relationlist, PakfireRelation relation) {
	queue_push(&relationlist->queue, pakfire_relation_get_id(relation));
}

PAKFIRE_EXPORT int pakfire_relationlist_count(PakfireRelationList relationlist) {
	return relationlist->queue.count;
}

PAKFIRE_EXPORT PakfireRelationList pakfire_relationlist_from_queue(Pakfire pakfire, Queue q) {
	PakfireRelationList relationlist = pakfire_relationlist_create(pakfire);
	if (relationlist) {
		// Release old queue
		queue_free(&relationlist->queue);

		// Copy the queue
		queue_init_clone(&relationlist->queue, &q);
	}

	return relationlist;
}

PAKFIRE_EXPORT PakfireRelation pakfire_relationlist_get_clone(PakfireRelationList relationlist, int index) {
	Id id = relationlist->queue.elements[index];

	return pakfire_relation_create_from_id(relationlist->pakfire, id);
}

PAKFIRE_EXPORT void pakfire_relationlist_clone_to_queue(PakfireRelationList relationlist, Queue* q) {
	queue_init_clone(q, &relationlist->queue);
}
