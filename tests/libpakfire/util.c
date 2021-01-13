/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2019 Pakfire development team                                 #
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

#include <string.h>

#include <pakfire/parser.h>
#include <pakfire/util.h>

#include "../testsuite.h"

static int test_basename(const struct test* t) {
	const char* dir = "/a/b/c";

	char* output = pakfire_basename(dir);
	ASSERT_STRING_EQUALS(output, "c");
	pakfire_free(output);

	return EXIT_SUCCESS;
}

static int test_dirname(const struct test* t) {
	const char* dir = "/a/b/c";

	char* output = pakfire_dirname(dir);
	ASSERT_STRING_EQUALS(output, "/a/b");
	pakfire_free(output);

	return EXIT_SUCCESS;
}

static int test_string_startswith(const struct test* t) {
	int r;

	r = pakfire_string_startswith("ABC", "A");
	ASSERT(r);

	r = pakfire_string_startswith("ABC", "B");
	ASSERT(!r);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_basename);
	testsuite_add_test(test_dirname);
	testsuite_add_test(test_string_startswith);

	return testsuite_run();
}
