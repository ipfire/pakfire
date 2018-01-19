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
#include <solv/repo.h>

#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/pakfire.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/types.h>
#include <pakfire/util.h>


// This is just being left here for compatibility
struct _PakfirePool {
	Pakfire pakfire;
	int nrefs;
};

PAKFIRE_EXPORT PakfirePool pakfire_pool_create(Pakfire pakfire) {
	PakfirePool pool = pakfire_calloc(1, sizeof(*pool));
	if (pool) {
		DEBUG("Allocated Pool at %p\n", pool);
		pool->nrefs = 1;

		pool->pakfire = pakfire_ref(pakfire);
	}

	return pool;
}

static void pakfire_pool_free(PakfirePool pool) {
	pakfire_unref(pool->pakfire);
	pakfire_free(pool);

	DEBUG("Released Pool at %p\n", pool);
}

PAKFIRE_EXPORT PakfirePool pakfire_pool_ref(PakfirePool pool) {
	++pool->nrefs;

	return pool;
}

PAKFIRE_EXPORT PakfirePool pakfire_pool_unref(PakfirePool pool) {
	if (!pool)
		return NULL;

	if (--pool->nrefs > 0)
		return pool;

	pakfire_pool_free(pool);
	return NULL;
}

Pool* pakfire_pool_get_solv_pool(PakfirePool pool) {
	return pakfire_get_solv_pool(pool->pakfire);
}
