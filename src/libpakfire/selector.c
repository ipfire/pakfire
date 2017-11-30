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

#include <solv/pool.h>
#include <solv/queue.h>
#include <solv/solver.h>

#include <pakfire/errno.h>
#include <pakfire/filter.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/selector.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PAKFIRE_EXPORT PakfireSelector pakfire_selector_create(PakfirePool pool) {
	PakfireSelector selector = pakfire_calloc(1, sizeof(*selector));
	selector->pool = pool;

	selector->f_arch = NULL;
	selector->f_name = NULL;
	selector->f_evr = NULL;
	selector->f_provides = NULL;

	return selector;
}

PAKFIRE_EXPORT void pakfire_selector_free(PakfireSelector selector) {
	pakfire_free(selector);
}

static int pakfire_selector_valid_setting(int keyname, int cmp_type) {
	switch (keyname) {
		case PAKFIRE_PKG_ARCH:
		case PAKFIRE_PKG_EVR:
		case PAKFIRE_PKG_VERSION:
		case PAKFIRE_PKG_PROVIDES:
			return cmp_type == PAKFIRE_EQ;

		case PAKFIRE_PKG_NAME:
			return (cmp_type == PAKFIRE_EQ || cmp_type == PAKFIRE_GLOB);

		default:
			return 0;
	}
}

static void pakfire_selector_replace_filter(PakfireFilter* filter, int keyname, int cmp_type, const char* match) {
	if (*filter)
		pakfire_filter_free(*filter);

	PakfireFilter f = pakfire_filter_create();

	f->keyname = keyname;
	f->cmp_type = cmp_type;
	f->match = pakfire_strdup(match);

	*filter = f;
}

PAKFIRE_EXPORT int pakfire_selector_set(PakfireSelector selector, int keyname, int cmp_type, const char* match) {
	if (!pakfire_selector_valid_setting(keyname, cmp_type))
		return PAKFIRE_E_SELECTOR;

	PakfireFilter* filter = NULL;

	switch (keyname) {
		case PAKFIRE_PKG_ARCH:
			filter = &selector->f_arch;
			break;

		case PAKFIRE_PKG_EVR:
		case PAKFIRE_PKG_VERSION:
			filter = &selector->f_evr;
			break;

		case PAKFIRE_PKG_NAME:
			if (selector->f_provides)
				return PAKFIRE_E_SELECTOR;

			filter = &selector->f_name;
			break;

		case PAKFIRE_PKG_PROVIDES:
			if (selector->f_name)
				return PAKFIRE_E_SELECTOR;

			filter = &selector->f_provides;
			break;

		default:
			return PAKFIRE_E_SELECTOR; 
	}

	assert(filter);

	pakfire_selector_replace_filter(filter, keyname, cmp_type, match);

	return 0;
}

PAKFIRE_EXPORT PakfirePackageList pakfire_selector_providers(PakfireSelector selector) {
	Queue q;
	queue_init(&q);

	pakfire_selector2queue(selector, &q, 0);

	PakfirePackageList list = pakfire_packagelist_from_queue(selector->pool, &q);

	queue_free(&q);

	return list;
}

static int queue_has(Queue* queue, Id what, Id id) {
	for (int i = 0; i < queue->count; i += 2) {
		if (queue->elements[i] == what && queue->elements[i + 1] == id)
			return 1;
	}

	return 0;
}

static Id str2archid(Pool* pool, const char* arch) {
	// originally from libsolv/examples/solv.c:str2archid()

	if (!*arch)
        return 0;

    Id id = pool_str2id(pool, arch, 0);
    if (id == ARCH_SRC || id == ARCH_NOSRC || id == ARCH_NOARCH)
        return id;

    if (pool->id2arch && (id > pool->lastarch || !pool->id2arch[id]))
        return 0;

    return id;
}

static int filter_arch2queue(PakfirePool pool, const PakfireFilter f, Queue* queue) {
	if (f == NULL)
		return 0;

	assert(f->cmp_type == PAKFIRE_EQ);

	Pool* p = pakfire_pool_get_solv_pool(pool);
	Id archid = str2archid(p, f->match);
	if (archid == 0)
		return PAKFIRE_E_ARCH;

	for (int i = 0; i < queue->count; i += 2) {
		assert((queue->elements[i] & SOLVER_SELECTMASK) == SOLVER_SOLVABLE_NAME);

		Id dep = queue->elements[i + 1];
		queue->elements[i + 1] = pool_rel2id(p, dep, archid, REL_ARCH, 1);
		queue->elements[i] |= SOLVER_SETARCH;
	}

	return 0;
}

static int filter_evr2queue(PakfirePool pool, const PakfireFilter f, Queue* queue) {
	if (f == NULL)
		return 0;

	assert(f->cmp_type == PAKFIRE_EQ);

	Pool* p = pakfire_pool_get_solv_pool(pool);
	Id evr = pool_str2id(p, f->match, 1);

	for (int i = 0; i < queue->count; i += 2) {
		assert((queue->elements[i] & SOLVER_SELECTMASK) == SOLVER_SOLVABLE_NAME);

		Id dep = queue->elements[i + 1];
		queue->elements[i + 1] = pool_rel2id(p, dep, evr, REL_EQ, 1);
		queue->elements[i] |= PAKFIRE_PKG_VERSION ? SOLVER_SETEV : SOLVER_SETEVR;
	}

	return 0;
}

static int filter_name2queue(PakfirePool pool, const PakfireFilter f, Queue* queue) {
	if (f == NULL)
		return 0;

	Pool* p = pakfire_pool_get_solv_pool(pool);
	const char* name = f->match;
	Id id;
	Dataiterator di;

	switch (f->cmp_type) {
		case PAKFIRE_EQ:
			id = pool_str2id(p, name, 0);
			if (id)
				queue_push2(queue, SOLVER_SOLVABLE_NAME, id);
			break;

		case PAKFIRE_GLOB:
			dataiterator_init(&di, p, 0, 0, SOLVABLE_NAME, name, SEARCH_GLOB);

			while (dataiterator_step(&di)) {
				assert(di.idp);
				Id id = *di.idp;

				if (queue_has(queue, SOLVABLE_NAME, id))
					continue;

				queue_push2(queue, SOLVER_SOLVABLE_NAME, id);
			}

			dataiterator_free(&di);
			break;

		default:
			assert(0);
			return 1;
	}

	return 0;
}

static int filter_provides2queue(PakfirePool pool, const PakfireFilter f, Queue* queue) {
	if (f == NULL)
		return 0;

	Pool* p = pakfire_pool_get_solv_pool(pool);
	Id id;

	switch (f->cmp_type) {
		case PAKFIRE_EQ:
			id = pool_str2id(p, f->match, 0);
			if (id)
				queue_push2(queue, SOLVER_SOLVABLE_PROVIDES, id);
			break;

		default:
			assert(0);
			return 1;
	}

	return 0;
}

PAKFIRE_EXPORT int pakfire_selector2queue(const PakfireSelector selector, Queue* queue, int solver_action) {
	PakfirePool pool = selector->pool;
	int ret = 0;

	Queue queue_selector;
	queue_init(&queue_selector);

	if (selector->f_name == NULL && selector->f_provides == NULL) {
		// no name or provides in the selector is an erro
		ret = PAKFIRE_E_SELECTOR;
		goto finish;
	}

	pakfire_pool_apply_changes(pool);

	ret = filter_name2queue(pool, selector->f_name, &queue_selector);
	if (ret)
		goto finish;

	ret = filter_provides2queue(pool, selector->f_provides, &queue_selector);
	if (ret)
		goto finish;

	ret = filter_arch2queue(pool, selector->f_arch, &queue_selector);
	if (ret)
		goto finish;

	ret = filter_evr2queue(pool, selector->f_evr, &queue_selector);
	if (ret)
		goto finish;

	for (int i = 0; i < queue_selector.count; i += 2) {
		queue_push2(queue,
			queue_selector.elements[i] | solver_action,
			queue_selector.elements[i + 1]
		);
	}

finish:
	if (ret)
		pakfire_errno = ret;

	queue_free(&queue_selector);

	return ret;
}
