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

static int test_parser(const struct test* t) {
	char* value = NULL;

	// Create a new parser
	PakfireParser parser = pakfire_parser_create(t->pakfire, NULL, NULL);

	// Retrieve a value that does not exist
	value = pakfire_parser_get(parser, "null");
	ASSERT(!value);

	// Set a value
	int r = pakfire_parser_set(parser, "a", "a");
	ASSERT(r == 0);

	// Retrieve the value again
	value = pakfire_parser_get(parser, "a");
	ASSERT_STRING_EQUALS(value, "a");

	// Append something to the value
	r = pakfire_parser_append(parser, "a", "b");
	ASSERT(r == 0);

	// Retrieve the value again
	value = pakfire_parser_get(parser, "a");
	ASSERT_STRING_EQUALS(value, "a b");

	// Make a child parser
	PakfireParser subparser = pakfire_parser_create_child(parser, "child");
	ASSERT(subparser);

	// Try to get a again
	value = pakfire_parser_get(subparser, "a");
	ASSERT_STRING_EQUALS(value, "a b");

	// Append something to the subparser
	r = pakfire_parser_append(subparser, "a", "c");
	ASSERT(r == 0);

	// The subparser should return "a b c"
	value = pakfire_parser_get(subparser, "a");
	ASSERT_STRING_EQUALS(value, "a b c");

	// The original parser should remain unchanged
	value = pakfire_parser_get(parser, "a");
	ASSERT_STRING_EQUALS(value, "a b");

	// Set another value
	r = pakfire_parser_append(subparser, "b", "1");
	ASSERT(r == 0);

	// Merge the two parsers
	pakfire_parser_merge(parser, subparser);

	// Now a should have changed to "a b c"
	value = pakfire_parser_get(parser, "a");
	ASSERT_STRING_EQUALS(value, "a b c");

	// Set a variable
	r = pakfire_parser_set(parser, "c", "%{b}");
	ASSERT(r == 0);

	// Get the value of c
	value = pakfire_parser_get(parser, "c");
	ASSERT_STRING_EQUALS(value, "1");

	// Dump the parser
	char* s = pakfire_parser_dump(parser);
	printf("%s\n", s);

	// Cleanup
	pakfire_parser_unref(subparser);
	pakfire_parser_unref(parser);
	pakfire_free(value);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_parser);

	return testsuite_run();
}
