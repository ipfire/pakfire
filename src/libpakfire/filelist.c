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
#include <string.h>

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

PAKFIRE_EXPORT int pakfire_filelist_is_empty(PakfireFilelist list) {
	return list->size == 0;
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

	return pakfire_file_ref(list->elements[index]);
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

PAKFIRE_EXPORT void pakfire_filelist_sort(PakfireFilelist list) {
	// XXX TODO
}

static int pakfire_filelist_parse_line(PakfireFile* file, char* line, unsigned int format) {
	unsigned int i = 0;

	// Allocate file
	int r = pakfire_file_create(file);
	if (r)
		return r;

	ssize_t size;
	mode_t mode;
	time_t time;

	unsigned int bytes_read = 0;

	char* word = strtok(line, " ");
	while (word) {
		if (format >= 4) {
			switch (i) {
				// type
				case 0:
					pakfire_file_set_type(*file, *word);
					break;

				// size
				case 1:
					size = atoi(word);
					pakfire_file_set_size(*file, size);
					break;

				// user
				case 2:
					pakfire_file_set_user(*file, word);
					break;

				// group
				case 3:
					pakfire_file_set_group(*file, word);
					break;

				// mode
				case 4:
					mode = atoi(word);
					pakfire_file_set_mode(*file, mode);
					break;

				// time
				case 5:
					time = atoi(word);
					pakfire_file_set_time(*file, time);
					break;

				// checksum
				case 6:
					pakfire_file_set_chksum(*file, word);
					break;

				// name
				#warning handle filenames with spaces
				case 8:
					pakfire_file_set_name(*file, line + bytes_read);
					break;
			}

		} else if (format >= 3) {
			switch (i) {
				// name
				case 0:
					pakfire_file_set_name(*file, word);
					break;

				// type
				case 1:
					pakfire_file_set_type(*file, *word);
					break;

				// size
				case 2:
					size = atoi(word);
					pakfire_file_set_size(*file, size);
					break;

				// user
				case 3:
					pakfire_file_set_user(*file, word);
					break;

				// group
				case 4:
					pakfire_file_set_group(*file, word);
					break;

				// mode
				case 5:
					mode = atoi(word);
					pakfire_file_set_mode(*file, mode);
					break;

				// time
				case 6:
					time = atoi(word);
					pakfire_file_set_time(*file, time);
					break;

				// checksum
				case 7:
					pakfire_file_set_chksum(*file, word);
					break;
			}
		}

		// Count the bytes of the line that have been processed so far
		// (Skip all padding spaces)
		bytes_read += strlen(word) + 1;
		while (*(line + bytes_read) == ' ')
			bytes_read += 1;

		word = strtok(NULL, " ");
		++i;
	}

	return 0;
}

int pakfire_filelist_create_from_file(PakfireFilelist* list, const char* data, unsigned int format) {
	int r = pakfire_filelist_create(list);
	if (r)
		return r;

	PakfireFile file = NULL;

	char* p = (char *)data;
	char line[32 * 1024];

	for (;;) {
		line[0] = '\0';

		pakfire_sgets(line, sizeof(line), &p);
		pakfire_remove_trailing_newline(line);

		if (*line == '\0')
			break;

		int r = pakfire_filelist_parse_line(&file, line, format);
		if (r)
			goto ERROR;

		// Append file
		r = pakfire_filelist_append(*list, file);
		if (r)
			goto ERROR;

		pakfire_file_unref(file);
	}

	return 0;

ERROR:
	pakfire_filelist_unref(*list);

	return 1;
}
