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

#include <pakfire/file.h>
#include <pakfire/filelist.h>
#include <pakfire/private.h>
#include <pakfire/util.h>

struct _PakfireFilelist {
	PakfirePackage pkg;

	PakfireFile first;
	PakfireFile last;
};

PAKFIRE_EXPORT PakfireFilelist pakfire_filelist_create(PakfirePackage pkg) {
	PakfireFilelist list = pakfire_calloc(1, sizeof(*list));
	if (list) {
		list->pkg = pkg;

		list->first = NULL;
		list->last  = NULL;
	}

	return list;
}

PAKFIRE_EXPORT void pakfire_filelist_free(PakfireFilelist list) {
	pakfire_filelist_remove_all();
	pakfire_free(list);
}

static void pakfire_filelist_remove_first(PakfireFilelist list) {
	if (!list->first)
		return;

	PakfireFile file = list->first;

	list->first = file->next;
	list->first->prev = NULL;

	pakfire_file_free(file);
}

PAKFIRE_EXPORT void pakfire_filelist_remove_all(PakfireFilelist list) {
	while (list->first) {
		pakfire_filelist_remove_first(list);
	}
}

PAKFIRE_EXPORT void pakfire_filelist_append(PakfireFilelist list, PakfireFile file) {
	if (list->first && list->last) {
		list->last->next = file;
		list->last = file;
	} else {
		list->first = file;
		list->last  = file;
	}
}
