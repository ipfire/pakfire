/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2017 Pakfire development team                                 #
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

#ifndef PAKFIRE_TESTSUITE_H
#define PAKFIRE_TESTSUITE_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include <pakfire/pakfire.h>

#define MAX_TESTS 128

extern const char* TEST_SRC_PATH;

struct test {
	const char* name;
	int (*func)(const struct test* t);
	Pakfire pakfire;
};

struct testsuite {
	struct test tests[MAX_TESTS];
	size_t num;
} testsuite_t;

extern struct testsuite ts;

int __testsuite_add_test(const char* name, int (*func)(const struct test* t));
int testsuite_run();

#define _LOG(prefix, fmt, ...) fprintf(stderr, "TESTS: " prefix fmt, ## __VA_ARGS__);
#define LOG(fmt, ...) _LOG("", fmt, ## __VA_ARGS__);
#define LOG_WARN(fmt, ...) _LOG("WARN: ", fmt, ## __VA_ARGS__);
#define LOG_ERROR(fmt, ...) _LOG("ERROR: ", fmt, ## __VA_ARGS__);

#define testsuite_add_test(func) __testsuite_add_test(#func, func)

#define ASSERT(expr) \
	do { \
		if ((!(expr))) { \
			LOG_ERROR("Failed assertion: " #expr " %s:%d %s\n", \
				__FILE__, __LINE__, __PRETTY_FUNCTION__); \
			return EXIT_FAILURE; \
		} \
	} while (0)

#define ASSERT_STRING_EQUALS(string, value) \
	do { \
		if (strcmp(string, value) != 0) { \
			LOG_ERROR("Failed assertion: " #string " != " #value " %s:%d %s\n", \
				__FILE__, __LINE__, __PRETTY_FUNCTION__); \
			return EXIT_FAILURE; \
		} \
	} while (0)

#define ASSERT_STRING_STARTSWITH(string, start) \
	do { \
		if (strncmp(string, start, strlen(start)) != 0) { \
			LOG_ERROR("Failed assertion: " #string " does not start with " #start " %s:%d %s\n", \
				__FILE__, __LINE__, __PRETTY_FUNCTION__); \
			return EXIT_FAILURE; \
		} \
	} while (0)

#endif /* PAKFIRE_TESTSUITE_H */
