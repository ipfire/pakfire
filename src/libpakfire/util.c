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

#include <libgen.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <pakfire/constants.h>

void pakfire_oom(size_t num, size_t len) {
	if (num)
		fprintf(stderr, "Out of memory allocating %zu*%zu bytes!\n", num, len);
	else
		fprintf(stderr, "Out of memory allocating %zu bytes!\n", len);

	abort();
	exit(1);
}

void* pakfire_malloc(size_t len) {
	void* r = malloc(len ? len : 1);
	if (!r)
		pakfire_oom(0, len);

	return r;
}

void* pakfire_calloc(size_t num, size_t len) {
	void* r;

	if (num == 0 || len == 0)
		r = malloc(1);
	else
		r = calloc(num, len);

	if (!r)
		pakfire_oom(num, len);

	return r;
}

void* pakfire_realloc(void* ptr, size_t size) {
	ptr = realloc(ptr, size);
	if (!ptr)
		pakfire_oom(0, size);

	return ptr;
}

void* pakfire_free(void* mem) {
	if (mem)
		free(mem);

	return 0;
}

char* pakfire_strdup(const char* s) {
	if (!s)
		return 0;

	char* r = strdup(s);
	if (!r)
		pakfire_oom(0, strlen(s));

	return r;
}

char* pakfire_format_size(double size) {
	char string[STRING_SIZE];
	const char* units[] = {" ", "k", "M", "G", "T", NULL};
	const char** unit = units;

	while (*(unit + 1) && size >= 1024.0) {
		size /= 1024.0;
		unit++;
	}

	snprintf(string, STRING_SIZE, "%.0f%s", round(size), *unit);

	return pakfire_strdup(string);
}

char* pakfire_path_join(const char* first, const char* second) {
	char* buffer;

	if (!second)
		return pakfire_strdup(first);

	if (*second == '/')
		return pakfire_strdup(second);

	asprintf(&buffer, "%s/%s", first, second);

	return buffer;
}

char* pakfire_basename(const char* path) {
	char* name = pakfire_strdup(path);

	return basename(name);
}

char* pakfire_dirname(const char* path) {
	char* parent = pakfire_strdup(path);

	return dirname(parent);
}

char* pakfire_sgets(char* str, int num, char** input) {
	char* next = *input;
	int numread = 0;

	while (numread + 1 < num && *next) {
		int isnewline = (*next == '\n');

		*str++ = *next++;
		numread++;

		if (isnewline)
			break;
	}

	// Terminate string
	*str = '\0';

	*input = next;

	return str;
}

char* pakfire_remove_trailing_newline(char* str) {
	ssize_t pos = strlen(str) - 1;

	if (str[pos] == '\n')
		str[pos] = '\0';

	return str;
}
