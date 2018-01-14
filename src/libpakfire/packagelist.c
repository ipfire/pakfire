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

#include <stdlib.h>

#include <solv/pool.h>
#include <solv/pooltypes.h>
#include <solv/solver.h>
#include <solv/util.h>

#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/private.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define BLOCK_SIZE 31

PAKFIRE_EXPORT PakfirePackageList pakfire_packagelist_create(void) {
	PakfirePackageList list = pakfire_calloc(1, sizeof(*list));

	return list;
}

PAKFIRE_EXPORT void pakfire_packagelist_free(PakfirePackageList list) {
	for (int i = 0; i < list->count; i++) {
		PakfirePackage pkg = list->elements[i];
		pakfire_package_unref(pkg);
	}

	pakfire_free(list->elements);
	pakfire_free(list);
}

PAKFIRE_EXPORT int pakfire_packagelist_count(PakfirePackageList list) {
	return list->count;
}

PAKFIRE_EXPORT int _packagelist_cmp(const void* pkg1, const void* pkg2) {
	return pakfire_package_cmp(*(PakfirePackage*)pkg1, *(PakfirePackage*)pkg2);
}

PAKFIRE_EXPORT void pakfire_packagelist_sort(PakfirePackageList list) {
	qsort(list->elements, list->count, sizeof(*list->elements), _packagelist_cmp);
}

PAKFIRE_EXPORT PakfirePackage pakfire_packagelist_get(PakfirePackageList list, int index) {
	if (index < list->count)
		return list->elements[index];

	return NULL;
}

PAKFIRE_EXPORT int pakfire_packagelist_has(PakfirePackageList list, PakfirePackage pkg) {
	for (int i = 0; i < list->count; i++) {
		PakfirePackage _pkg = list->elements[i];

		if (pakfire_package_identical(pkg, _pkg))
			return 1;
	}

	return 0;
}

PAKFIRE_EXPORT void pakfire_packagelist_push(PakfirePackageList list, PakfirePackage pkg) {
	list->elements = solv_extend(list->elements, list->count, 1, sizeof(pkg), BLOCK_SIZE);
	list->elements[list->count++] = pakfire_package_ref(pkg);
}

PAKFIRE_EXPORT void pakfire_packagelist_push_if_not_exists(PakfirePackageList list, PakfirePackage pkg) {
	if (pakfire_packagelist_has(list, pkg))
		return;

	pakfire_packagelist_push(list, pkg);
}

PAKFIRE_EXPORT PakfirePackageList pakfire_packagelist_from_queue(PakfirePool _pool, Queue* q) {
	PakfirePackageList list = pakfire_packagelist_create();

	Pool* pool = pakfire_pool_get_solv_pool(_pool);
	Id p, pp;
	for (int i = 0; i < q->count; i += 2) {
		FOR_JOB_SELECT(p, pp, q->elements[i], q->elements[i + 1]) {
			PakfirePackage pkg = pakfire_package_create(_pool, p);
			pakfire_packagelist_push(list, pkg);
		}
	}

	return list;
}
