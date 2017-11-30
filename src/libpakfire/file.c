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

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <tar.h>
#include <time.h>

#include <pakfire/constants.h>
#include <pakfire/file.h>
#include <pakfire/private.h>
#include <pakfire/util.h>

PAKFIRE_EXPORT PakfireFile pakfire_file_create() {
	PakfireFile file = pakfire_calloc(1, sizeof(*file));
	if (file) {
		file->name = NULL;

		file->prev = NULL;
		file->next = NULL;
	}

	return file;
}

PAKFIRE_EXPORT void pakfire_file_free(PakfireFile file) {
	if (file->name)
		pakfire_free(file->name);

	if (file->user)
		pakfire_free(file->user);
	if (file->group)
		pakfire_free(file->group);

	// Update pointers in the previous and next element in the list.
	if (file->next)
		file->next->prev = NULL;
	if (file->prev)
		file->prev->next = NULL;

	pakfire_free(file);
}

PAKFIRE_EXPORT void pakfire_file_free_all(PakfireFile file) {
	file = pakfire_file_get_first(file);

	while (file) {
		PakfireFile next = file->next;
		pakfire_file_free(file);

		file = next;
	}
}

PAKFIRE_EXPORT int pakfire_file_cmp(PakfireFile file1, PakfireFile file2) {
	const char* name1 = pakfire_file_get_name(file1);
	const char* name2 = pakfire_file_get_name(file2);

	return strcmp(name1, name2);
}

PAKFIRE_EXPORT void pakfire_file_swap(PakfireFile file1, PakfireFile file2) {
	PakfireFile file_prev = file1->prev;
	PakfireFile file_next = file2->next;

	if (file_prev)
		file_prev->next = file2;
	file2->prev = file_prev;

	if (file_next)
		file_next->prev = file1;
	file1->next = file_next;

	file2->next = file1;
	file1->prev = file2;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_sort(PakfireFile head) {
	unsigned int count = pakfire_file_count(head);

	for (unsigned int i = 0; i < count; i++) {
		PakfireFile file = head;
		PakfireFile next = pakfire_file_get_next(file);

		while (next) {
			if (pakfire_file_cmp(file, next) > 0) {
				if (head == file)
					head = next;

				pakfire_file_swap(file, next);
			}

			file = next;
			next = pakfire_file_get_next(file);
		}
	}

	return head;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_get_prev(PakfireFile file) {
	return file->prev;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_get_next(PakfireFile file) {
	return file->next;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_get_first(PakfireFile file) {
	if (file->prev)
		return pakfire_file_get_first(file->prev);

	return file;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_get_last(PakfireFile file) {
	if (file->next)
		return pakfire_file_get_last(file->next);

	return file;
}

static PakfireFile __pakfire_file_append(PakfireFile file, PakfireFile appended_file) {
	// Get the last file in the queue.
	file = pakfire_file_get_last(file);

	// Set the links.
	file->next = appended_file;
	appended_file->prev = file;

	return appended_file;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_append(PakfireFile file) {
	// Create a new file object.
	PakfireFile appended_file = pakfire_file_create();

	return __pakfire_file_append(file, appended_file);
}

PAKFIRE_EXPORT unsigned int pakfire_file_count(PakfireFile file) {
	unsigned int counter = 0;

	while (file) {
		file = pakfire_file_get_next(file);
		++counter;
	}

	return counter;
}

static char pakfire_file_sprintf_type(PakfireFile file) {
	if (pakfire_file_is_dir(file))
		return 'd';

	if (pakfire_file_is_symlink(file))
		return 'l';

	if (pakfire_file_is_char(file))
		return 'c';

	return '-';
}

static char* pakfire_file_format_perms(PakfireFile file) {
	char buffer[11];

	mode_t mode = pakfire_file_get_mode(file);

	buffer[0] = pakfire_file_sprintf_type(file);
	buffer[1] = (S_IRUSR & mode) ? 'r' : '-';
	buffer[2] = (S_IWUSR & mode) ? 'w' : '-';
	buffer[3] = (S_IXUSR & mode) ? 'x' : '-';
	buffer[4] = (S_IRGRP & mode) ? 'r' : '-';
	buffer[5] = (S_IWGRP & mode) ? 'w' : '-';
	buffer[6] = (S_IXGRP & mode) ? 'x' : '-';
	buffer[7] = (S_IROTH & mode) ? 'r' : '-';
	buffer[8] = (S_IWOTH & mode) ? 'w' : '-';
	buffer[9] = (S_IXOTH & mode) ? 'x' : '-';
	buffer[10] = '\0';

	#warning TODO SUID bits, etc...

	return pakfire_strdup(buffer);
}

static char* pakfire_file_format_mtime(PakfireFile file) {
	struct tm* timer = gmtime((time_t *)&file->time);

	char buffer[STRING_SIZE];
	strftime(buffer, sizeof(buffer), "%d %b %Y %T", timer);

	return pakfire_strdup(buffer);
}

PAKFIRE_EXPORT void pakfire_file_sprintf(PakfireFile file, char* str, size_t len) {
	const char* name = pakfire_file_get_name(file);
	ssize_t size = pakfire_file_get_size(file);

	const char* user  = pakfire_file_get_user(file);
	const char* group = pakfire_file_get_group(file);

	char* perms = pakfire_file_format_perms(file);
	char* mtime = pakfire_file_format_mtime(file);

	snprintf(str, len, "%s %-8s %-8s %8d %s %s", perms, user, group,
		(int)size, mtime, name);

	pakfire_free(perms);
	pakfire_free(mtime);
}

PAKFIRE_EXPORT const char* pakfire_file_get_name(PakfireFile file) {
	return file->name;
}

PAKFIRE_EXPORT void pakfire_file_set_name(PakfireFile file, const char* name) {
	if (file->name)
		pakfire_free(file->name);

	if (*name == '/') {
		file->name = pakfire_strdup(name);
	} else {
		asprintf(&file->name, "/%s", name);
	}
}

PAKFIRE_EXPORT char pakfire_file_get_type(PakfireFile file) {
	return file->type;
}

PAKFIRE_EXPORT void pakfire_file_set_type(PakfireFile file, char type) {
	file->type = type;
}

PAKFIRE_EXPORT int pakfire_file_is_file(PakfireFile file) {
	return (file->type == REGTYPE) || (file->type == AREGTYPE);
}

PAKFIRE_EXPORT int pakfire_file_is_link(PakfireFile file) {
	return (file->type == LNKTYPE);
}

PAKFIRE_EXPORT int pakfire_file_is_symlink(PakfireFile file) {
	return (file->type == SYMTYPE);
}

PAKFIRE_EXPORT int pakfire_file_is_char(PakfireFile file) {
	return (file->type == CHRTYPE);
}

PAKFIRE_EXPORT int pakfire_file_is_block(PakfireFile file) {
	return (file->type == BLKTYPE);
}

PAKFIRE_EXPORT int pakfire_file_is_dir(PakfireFile file) {
	return (file->type == DIRTYPE);
}

PAKFIRE_EXPORT ssize_t pakfire_file_get_size(PakfireFile file) {
	return file->size;
}

PAKFIRE_EXPORT void pakfire_file_set_size(PakfireFile file, ssize_t size) {
	file->size = size;
}

PAKFIRE_EXPORT const char* pakfire_file_get_user(PakfireFile file) {
	return file->user;
}

PAKFIRE_EXPORT void pakfire_file_set_user(PakfireFile file, const char* user) {
	file->user = pakfire_strdup(user);
}

PAKFIRE_EXPORT const char* pakfire_file_get_group(PakfireFile file) {
	return file->group;
}

PAKFIRE_EXPORT void pakfire_file_set_group(PakfireFile file, const char* group) {
	file->group = pakfire_strdup(group);
}

PAKFIRE_EXPORT mode_t pakfire_file_get_mode(PakfireFile file) {
	return file->mode;
}

PAKFIRE_EXPORT void pakfire_file_set_mode(PakfireFile file, mode_t mode) {
	file->mode = mode;
}

PAKFIRE_EXPORT time_t pakfire_file_get_time(PakfireFile file) {
	return file->time;
}

PAKFIRE_EXPORT void pakfire_file_set_time(PakfireFile file, time_t time) {
	file->time = time;
}

PAKFIRE_EXPORT const char* pakfire_file_get_chksum(PakfireFile file) {
	return file->chksum;
}

PAKFIRE_EXPORT void pakfire_file_set_chksum(PakfireFile file, const char* chksum) {
	file->chksum = pakfire_strdup(chksum);
}

static PakfireFile pakfire_file_parse_line(char* line, unsigned int format) {
	unsigned int i = 0;

	PakfireFile file = pakfire_file_create();
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
					pakfire_file_set_type(file, *word);
					break;

				// size
				case 1:
					size = atoi(word);
					pakfire_file_set_size(file, size);
					break;

				// user
				case 2:
					pakfire_file_set_user(file, word);
					break;

				// group
				case 3:
					pakfire_file_set_group(file, word);
					break;

				// mode
				case 4:
					mode = atoi(word);
					pakfire_file_set_mode(file, mode);
					break;

				// time
				case 5:
					time = atoi(word);
					pakfire_file_set_time(file, time);
					break;

				// checksum
				case 6:
					pakfire_file_set_chksum(file, word);
					break;

				// name
				#warning handle filenames with spaces
				case 8:
					pakfire_file_set_name(file, line + bytes_read);
					break;
			}

		} else if (format >= 3) {
			switch (i) {
				// name
				case 0:
					pakfire_file_set_name(file, word);
					break;

				// type
				case 1:
					pakfire_file_set_type(file, *word);
					break;

				// size
				case 2:
					size = atoi(word);
					pakfire_file_set_size(file, size);
					break;

				// user
				case 3:
					pakfire_file_set_user(file, word);
					break;

				// group
				case 4:
					pakfire_file_set_group(file, word);
					break;

				// mode
				case 5:
					mode = atoi(word);
					pakfire_file_set_mode(file, mode);
					break;

				// time
				case 6:
					time = atoi(word);
					pakfire_file_set_time(file, time);
					break;

				// checksum
				case 7:
					pakfire_file_set_chksum(file, word);
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

	return file;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_parse_from_file(const char* list, unsigned int format) {
	PakfireFile head = NULL;

	char* plist = (char *)list;
	char line[32 * 1024];

	for (;;) {
		line[0] = '\0';

		pakfire_sgets(line, sizeof(line), &plist);
		pakfire_remove_trailing_newline(line);

		if (*line == '\0')
			break;

		PakfireFile file = pakfire_file_parse_line(line, format);

		if (!file)
			continue;

		if (head)
			file = __pakfire_file_append(head, file);
		else
			head = file;
	}

	return head;
}
