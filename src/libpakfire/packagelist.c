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

#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/pakfire.h>
#include <pakfire/private.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define BLOCK_SIZE 31

struct _PakfirePackageList {
	Pakfire pakfire;
	PakfirePackage* elements;
	size_t count;
	int nrefs;
};

PAKFIRE_EXPORT PakfirePackageList pakfire_packagelist_create(Pakfire pakfire) {
	PakfirePackageList list = pakfire_calloc(1, sizeof(*list));
	if (list) {
		DEBUG(pakfire, "Allocated PackageList at %p\n", list);
		list->pakfire = pakfire_ref(pakfire);
		list->nrefs = 1;
	}

	return list;
}

PAKFIRE_EXPORT PakfirePackageList pakfire_packagelist_ref(PakfirePackageList list) {
	list->nrefs++;

	return list;
}

static void pakfire_packagelist_free(PakfirePackageList list) {
	DEBUG(list->pakfire, "Releasing PackageList at %p\n", list);
	pakfire_unref(list->pakfire);

	for (unsigned int i = 0; i < list->count; i++) {
		pakfire_package_unref(list->elements[i]);
	}

	pakfire_free(list->elements);
	pakfire_free(list);
}

PAKFIRE_EXPORT PakfirePackageList pakfire_packagelist_unref(PakfirePackageList list) {
	if (!list)
		return NULL;

	if (--list->nrefs > 0)
		return list;

	pakfire_packagelist_free(list);
	return NULL;
}

PAKFIRE_EXPORT size_t pakfire_packagelist_count(PakfirePackageList list) {
	return list->count;
}

PAKFIRE_EXPORT int _packagelist_cmp(const void* pkg1, const void* pkg2) {
	return pakfire_package_cmp(*(PakfirePackage*)pkg1, *(PakfirePackage*)pkg2);
}

PAKFIRE_EXPORT void pakfire_packagelist_sort(PakfirePackageList list) {
	qsort(list->elements, list->count, sizeof(*list->elements), _packagelist_cmp);
}

PAKFIRE_EXPORT PakfirePackage pakfire_packagelist_get(PakfirePackageList list, unsigned int index) {
	if (index < list->count)
		return pakfire_package_ref(list->elements[index]);

	return NULL;
}

PAKFIRE_EXPORT int pakfire_packagelist_has(PakfirePackageList list, PakfirePackage pkg) {
	for (unsigned int i = 0; i < list->count; i++) {
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

PAKFIRE_EXPORT PakfirePackageList pakfire_packagelist_from_queue(Pakfire pakfire, Queue* q) {
	PakfirePackageList list = pakfire_packagelist_create(pakfire);

	Pool* pool = pakfire_get_solv_pool(pakfire);
	Id p, pp;
	for (int i = 0; i < q->count; i += 2) {
		FOR_JOB_SELECT(p, pp, q->elements[i], q->elements[i + 1]) {
			PakfirePackage pkg = pakfire_package_create(pakfire, p);
			pakfire_packagelist_push(list, pkg);

			pakfire_package_unref(pkg);
		}
	}

	return list;
}
