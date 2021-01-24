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
#include <errno.h>
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

struct _PakfireFile {
	int nrefs;

	char* name;
	char type;
	ssize_t size;

	char* user;
	char* group;

	mode_t mode;
	time_t time;

	char* chksum;

	#warning TODO capabilities, config, data
	// capabilities
	//int is_configfile;
	//int is_datafile;
};

PAKFIRE_EXPORT int pakfire_file_create(PakfireFile* file) {
	PakfireFile f = pakfire_calloc(1, sizeof(*f));
	if (!f)
		return -ENOMEM;

	f->nrefs = 1;

	*file = f;
	return 0;
}

static void pakfire_file_free(PakfireFile file) {
	if (file->name)
		pakfire_free(file->name);
	if (file->user)
		pakfire_free(file->user);
	if (file->group)
		pakfire_free(file->group);
	if (file->chksum)
		pakfire_free(file->chksum);

	pakfire_free(file);
}

PAKFIRE_EXPORT PakfireFile pakfire_file_ref(PakfireFile file) {
	file->nrefs++;

	return file;
}

PAKFIRE_EXPORT PakfireFile pakfire_file_unref(PakfireFile file) {
	if (--file->nrefs > 0)
		return file;

	pakfire_file_free(file);
	return NULL;
}

PAKFIRE_EXPORT int pakfire_file_cmp(PakfireFile file1, PakfireFile file2) {
	const char* name1 = pakfire_file_get_name(file1);
	const char* name2 = pakfire_file_get_name(file2);

	return strcmp(name1, name2);
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

PAKFIRE_EXPORT char* pakfire_file_get_dirname(PakfireFile file) {
	return pakfire_dirname(file->name);
}

PAKFIRE_EXPORT char* pakfire_file_get_basename(PakfireFile file) {
	return pakfire_basename(file->name);
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
