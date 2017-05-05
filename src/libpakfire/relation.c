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

#include <assert.h>

#include <solv/pooltypes.h>
#include <solv/queue.h>
#include <solv/solver.h>

#include <pakfire/packagelist.h>
#include <pakfire/pool.h>
#include <pakfire/relation.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

static int cmptype2relflags(int type) {
	int flags = 0;

	if (type & PAKFIRE_EQ)
		flags |= REL_EQ;
	if (type & PAKFIRE_LT)
		flags |= REL_LT;
	if (type & PAKFIRE_GT)
		flags |= REL_GT;

	return flags;
}

PakfireRelation pakfire_relation_create(PakfirePool pool, const char* name, int cmp_type, const char* evr) {
	Pool* p = pool->pool;

	Id id = pool_str2id(p, name, 1);

	if (id == STRID_NULL || id == STRID_EMPTY)
		return NULL;

	if (evr) {
		assert(cmp_type);

		Id ievr = pool_str2id(p, evr, 1);
		int flags = cmptype2relflags(cmp_type);
		id = pool_rel2id(p, id, ievr, flags, 1);
	}

	return pakfire_relation_create_from_id(pool, id);
}

PakfireRelation pakfire_relation_create_from_id(PakfirePool pool, Id id) {
	PakfireRelation relation = pakfire_calloc(1, sizeof(*relation));

	relation->pool = pool;
	relation->id = id;

	return relation;
}

void pakfire_relation_free(PakfireRelation relation) {
	pakfire_free(relation);
}

Id pakfire_relation_id(PakfireRelation relation) {
	return relation->id;
}

char* pakfire_relation_str(PakfireRelation relation) {
	Pool* pool = pakfire_relation_solv_pool(relation);

	const char* str = pool_dep2str(pool, relation->id);

	return pakfire_strdup(str);
}

int pakfire_relation2queue(const PakfireRelation relation, Queue* queue, int solver_action) {
	queue_push2(queue, SOLVER_SOLVABLE_PROVIDES|solver_action, relation->id);

	return 0;
}

PakfirePackageList pakfire_relation_providers(PakfireRelation relation) {
	Queue q;
	queue_init(&q);

	pakfire_relation2queue(relation, &q, 0);

	PakfirePackageList list = pakfire_packagelist_from_queue(relation->pool, &q);

	queue_free(&q);

	return list;
}