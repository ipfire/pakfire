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

PAKFIRE_EXPORT int pakfire_string_startswith(const char* s, const char* prefix) {
	return !strncmp(s, prefix, strlen(prefix));
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

	if (!first)
		return pakfire_strdup(second);

	if (!second)
		return pakfire_strdup(first);

	if (*second == '/')
		return pakfire_strdup(second);

	asprintf(&buffer, "%s/%s", first, second);

	return buffer;
}

PAKFIRE_EXPORT const char* pakfire_path_relpath(const char* root, const char* path) {
	if (pakfire_string_startswith(path, root))
		return path + strlen(root);

	return NULL;
}

PAKFIRE_EXPORT int pakfire_path_isdir(const char* path) {
	struct stat s;

	if (stat(path, &s) != 0) {
		// Does not seem to exist
		return 0;
	}

	if (S_ISDIR(s.st_mode))
		return 1;

	return 0;
}

PAKFIRE_EXPORT char* pakfire_basename(const char* path) {
	char* name = pakfire_strdup(path);

	char* r = basename(name);
	if (r)
		r = pakfire_strdup(r);

	pakfire_free(name);

	return r;
}

PAKFIRE_EXPORT char* pakfire_dirname(const char* path) {
	char* parent = pakfire_strdup(path);

	char* r = dirname(parent);
	if (r)
		r = pakfire_strdup(r);

	pakfire_free(parent);

	return r;
}

PAKFIRE_EXPORT int pakfire_access(Pakfire pakfire, const char* dir, const char* file, int mode) {
	char* path = pakfire_path_join(dir, file);

	int r = access(path, mode);

	if (r) {
		if (mode & R_OK)
			DEBUG(pakfire, "%s is not readable\n", path);

		if (mode & W_OK)
			DEBUG(pakfire, "%s is not writable\n", path);

		if (mode & X_OK)
			DEBUG(pakfire, "%s is not executable\n", path);

		if (mode & F_OK)
			DEBUG(pakfire, "%s does not exist\n", path);
	}

	pakfire_free(path);

	return r;
}

int pakfire_mkdir(Pakfire pakfire, const char* path, mode_t mode) {
	int r = 0;

	if ((strcmp(path, "/") == 0) || (strcmp(path, ".") == 0))
		return 0;

	// If parent does not exists, we try to create it.
	char* parent = pakfire_dirname(path);
	r = pakfire_access(pakfire, parent, NULL, F_OK);
	if (r)
		r = pakfire_mkdir(pakfire, parent, 0);

	pakfire_free(parent);

	// Exit if parent directory could not be created
	if (r)
		return r;

	DEBUG(pakfire, "Creating directory %s\n", path);

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

PAKFIRE_EXPORT int pakfire_read_file_into_buffer(FILE* f, char** buffer, size_t* len) {
	if (!f)
		return -EBADF;

	int r = fseek(f, 0, SEEK_END);
	if (r)
		return r;

	// Save length of file
	*len = ftell(f);

	// Go back to the start
	r = fseek(f, 0, SEEK_SET);
	if (r)
		return r;

	// Allocate buffer
	*buffer = pakfire_malloc((sizeof(**buffer) * *len) + 1);
	if (!*buffer)
		return -ENOMEM;

	// Read content
	fread(*buffer, *len, sizeof(**buffer), f);

	// Check we encountered any errors
	r = ferror(f);
	if (r) {
		pakfire_free(*buffer);
		return r;
	}

	// Terminate the buffer
	(*buffer)[*len] = '\0';

	return 0;
}

PAKFIRE_EXPORT size_t pakfire_string_to_size(const char* s) {
	size_t size;

	int r = sscanf(s, "%zu", &size);
	if (r == 1)
		return size;

	return 0;
}

PAKFIRE_EXPORT char** pakfire_split_string(const char* s, char delim) {
	// Copy string to stack and count spaces
	char buffer[strlen(s) + 2];

	size_t count = 1;
	for (unsigned int i = 0; i < strlen(s) + 1; i++) {
		buffer[i] = s[i];

		if (s[i] == delim) {
			buffer[i] = '\0';
			count++;
		}
	}

	// Allocate an array of sufficient size
	char** ret = pakfire_malloc(sizeof(*ret) * (count + 1));

	// Copy strings to heap one by one
	unsigned int i = 0;
	char* p = buffer;
	while (*p) {
		ret[i++] = pakfire_strdup(p);

		// Move pointer to the next string
		p += strlen(p) + 1;
	}

	// Terminate array
	ret[count] = NULL;

	return ret;
}

PAKFIRE_EXPORT void pakfire_partition_string(const char* s, const char* delim, char** s1, char** s2) {
	char* p = strstr(s, delim);

	// Delim was not found
	if (!p) {
		*s1 = NULL;
		*s2 = NULL;
		return;
	}

	// Length of string before delim
	size_t l = p - s;

	*s1 = pakfire_malloc(l);
	snprintf(*s1, l, "%s", s);

	*s2 = pakfire_strdup(p + strlen(delim));
}
