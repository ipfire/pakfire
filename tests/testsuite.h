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

#include <stdlib.h>
#include <stdio.h>

// Forward declaration
struct test;

typedef int (*test_function_t)(const struct test* t);

typedef struct test {
	const char* name;
	test_function_t func;
} test_t;

typedef struct testsuite {
	test_t** tests;
	size_t left;
} testsuite_t;

int testsuite_init();
testsuite_t* testsuite_create(size_t n);
int testsuite_add_test(testsuite_t* ts, const char* name, test_function_t func);
int testsuite_run(testsuite_t* ts);

int test_run(const test_t* t);

#define _LOG(prefix, fmt, ...) printf("TESTS: " prefix fmt, ## __VA_ARGS__);
#define LOG(fmt, ...) _LOG("", fmt, ## __VA_ARGS__);
#define LOG_WARN(fmt, ...) _LOG("WARN: ", fmt, ## __VA_ARGS__);
#define LOG_ERROR(fmt, ...) _LOG("ERROR: ", fmt, ## __VA_ARGS__);

#define assert_return(expr, r) \
	do { \
		if ((!(expr))) { \
			ERR_("Failed assertion: " #expr " %s:%d %s\n", \
				__FILE__, __LINE__, __PRETTY_FUNCTION__); \
			return r; \
		} \
	} while (0)