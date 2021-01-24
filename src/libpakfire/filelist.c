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

#include <errno.h>
#include <stdlib.h>

#include <pakfire/file.h>
#include <pakfire/filelist.h>
#include <pakfire/private.h>
#include <pakfire/util.h>

struct _PakfireFilelist {
	int nrefs;

	PakfireFile* elements;
	size_t elements_size;

	size_t size;
};

static int pakfire_filelist_grow(PakfireFilelist list, size_t size) {
	PakfireFile* elements = reallocarray(list->elements,
		list->elements_size + size, sizeof(*list->elements));
	if (!elements)
		return -errno;

	list->elements = elements;
	list->elements_size += size;

	return 0;
}

PAKFIRE_EXPORT int pakfire_filelist_create(PakfireFilelist* list) {
	PakfireFilelist l = pakfire_calloc(1, sizeof(*l));
	if (!l)
		return -ENOMEM;

	l->nrefs = 1;

	*list = l;
	return 0;
}

static void pakfire_filelist_free(PakfireFilelist list) {
	pakfire_filelist_clear(list);
	pakfire_free(list);
}

PAKFIRE_EXPORT PakfireFilelist pakfire_filelist_ref(PakfireFilelist list) {
	list->nrefs++;

	return list;
}

PAKFIRE_EXPORT PakfireFilelist pakfire_filelist_unref(PakfireFilelist list) {
	if (--list->nrefs > 0)
		return list;

	pakfire_filelist_free(list);
	return NULL;
}

PAKFIRE_EXPORT size_t pakfire_filelist_size(PakfireFilelist list) {
	return list->size;
}

PAKFIRE_EXPORT void pakfire_filelist_clear(PakfireFilelist list) {
	if (!list->elements)
		return;

	for (unsigned int i = 0; i < list->size; i++)
		pakfire_file_unref(list->elements[i]);

	free(list->elements);
	list->elements = NULL;
	list->elements_size = 0;

	list->size = 0;
}

PAKFIRE_EXPORT PakfireFile pakfire_filelist_get(PakfireFilelist list, size_t index) {
	if (index >= list->size)
		return NULL;

	return list->elements[index];
}

PAKFIRE_EXPORT int pakfire_filelist_append(PakfireFilelist list, PakfireFile file) {
	// Check if we have any space left
	if (list->size >= list->elements_size) {
		int r = pakfire_filelist_grow(list, 64);
		if (r)
			return r;
	}

	list->elements[list->size++] = pakfire_file_ref(file);

	return 0;
}
