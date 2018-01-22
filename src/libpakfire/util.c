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

#include <errno.h>
#include <libgen.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include <gcrypt.h>

#include <pakfire/constants.h>
#include <pakfire/logging.h>
#include <pakfire/private.h>
#include <pakfire/types.h>

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

PAKFIRE_EXPORT void* pakfire_free(void* mem) {
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

int pakfire_string_startswith(const char* s, const char* prefix) {
	return strncmp(s, prefix, strlen(prefix));
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

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wformat-nonliteral"
static char* pakfire_strftime(const char* format, time_t t) {
	char string[STRING_SIZE];
	struct tm* tm = gmtime(&t);

	strftime(string, sizeof(string), format, tm);

	return pakfire_strdup(string);
}
#pragma GCC diagnostic pop

char* pakfire_format_date(time_t t) {
	return pakfire_strftime("%Y-%m-%d", t);
}

PAKFIRE_EXPORT char* pakfire_path_join(const char* first, const char* second) {
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

PAKFIRE_EXPORT int pakfire_access(const char* dir, const char* file, int mode) {
	char* path = pakfire_path_join(dir, file);

	int r = access(path, mode);

	if (r) {
		if (mode & R_OK)
			DEBUG("%s is not readable\n", path);

		if (mode & W_OK)
			DEBUG("%s is not writable\n", path);

		if (mode & X_OK)
			DEBUG("%s is not executable\n", path);

		if (mode & F_OK)
			DEBUG("%s does not exist\n", path);
	}

	return r;
}

int pakfire_mkdir(const char* path, mode_t mode) {
	int r = 0;

	if ((strcmp(path, "/") == 0) || (strcmp(path, ".") == 0))
		return 0;

	// If parent does not exists, we try to create it.
	char* parent = pakfire_dirname(path);
	r = pakfire_access(parent, NULL, F_OK);
	if (r)
		r = pakfire_mkdir(parent, 0);

	pakfire_free(parent);

	if (r)
		return r;

	// Finally, create the directory we want.
	r = mkdir(path, mode);
	if (r) {
		switch (errno) {
			// If the directory already exists, this is fine.
			case EEXIST:
				r = 0;
				break;
		}
	}

	return r;
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

void init_libgcrypt() {
	// Only execute this once
	static int libgcrypt_initialized = 0;
	if (libgcrypt_initialized++)
		return;

	const char* version = gcry_check_version(NULL);
	if (!version) {
		fprintf(stderr, "Could not initialize libgcrypt\n");
		exit(1);
	}

	// Disable secure memory
	gcry_control(GCRYCTL_DISABLE_SECMEM, 0);

	// Tell libgcrypt that initialization has completed
	gcry_control(GCRYCTL_INITIALIZATION_FINISHED, 0);
}

PAKFIRE_EXPORT const char* pakfire_action_type_string(pakfire_action_type_t type) {
	switch (type) {
		case PAKFIRE_ACTION_NOOP:
			return "NOOP";

		case PAKFIRE_ACTION_VERIFY:
			return "VERIFY";

		case PAKFIRE_ACTION_EXECUTE:
			return "EXECUTE";

		case PAKFIRE_ACTION_PRETRANS:
			return "PRETRANS";

		case PAKFIRE_ACTION_POSTTRANS:
			return "POSTTRANS";
	}

	return NULL;
}
