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

#ifndef PAKFIRE_FILE_H
#define PAKFIRE_FILE_H

#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include <pakfire/types.h>

PakfireFile pakfire_file_create();

PakfireFile pakfire_file_ref(PakfireFile file);
PakfireFile pakfire_file_unref(PakfireFile file);

void pakfire_file_free(PakfireFile file);
void pakfire_file_free_all(PakfireFile file);

int pakfire_file_cmp(PakfireFile file1, PakfireFile file2);
void pakfire_file_swap(PakfireFile file1, PakfireFile file2);
PakfireFile pakfire_file_sort(PakfireFile head);

PakfireFile pakfire_file_get_prev(PakfireFile file);
PakfireFile pakfire_file_get_next(PakfireFile file);
PakfireFile pakfire_file_get_first(PakfireFile file);
PakfireFile pakfire_file_get_last(PakfireFile file);

PakfireFile pakfire_file_append(PakfireFile file);

unsigned int pakfire_file_count(PakfireFile file);

void pakfire_file_sprintf(PakfireFile file, char* str, size_t len);

const char* pakfire_file_get_name(PakfireFile file);
void pakfire_file_set_name(PakfireFile file, const char* name);

char pakfire_file_get_type(PakfireFile file);
void pakfire_file_set_type(PakfireFile file, char type);

int pakfire_file_is_file(PakfireFile file);
int pakfire_file_is_link(PakfireFile file);
int pakfire_file_is_symlink(PakfireFile file);
int pakfire_file_is_char(PakfireFile file);
int pakfire_file_is_block(PakfireFile file);
int pakfire_file_is_dir(PakfireFile file);

ssize_t pakfire_file_get_size(PakfireFile file);
void pakfire_file_set_size(PakfireFile file, ssize_t size);

const char* pakfire_file_get_user(PakfireFile file);
void pakfire_file_set_user(PakfireFile file, const char* user);

const char* pakfire_file_get_group(PakfireFile file);
void pakfire_file_set_group(PakfireFile file, const char* group);

mode_t pakfire_file_get_mode(PakfireFile file);
void pakfire_file_set_mode(PakfireFile file, mode_t mode);

time_t pakfire_file_get_time(PakfireFile file);
void pakfire_file_set_time(PakfireFile file, time_t time);

const char* pakfire_file_get_chksum(PakfireFile file);
void pakfire_file_set_chksum(PakfireFile file, const char* chksum);

PakfireFile pakfire_file_parse_from_file(const char* list, unsigned int format);

#ifdef PAKFIRE_PRIVATE

struct _PakfireFile {
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

	PakfireFile prev;
	PakfireFile next;
};

#endif

#endif /* PAKFIRE_FILE_H */
