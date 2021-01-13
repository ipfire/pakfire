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

static int test_parser(const test_t* t) {
	char* value = NULL;

	// Create a new parser
	PakfireParser parser = pakfire_parser_create(t->pakfire, NULL, NULL);

	// Retrieve a value that does not exist
	value = pakfire_parser_get(parser, "null");
	assert_return(!value, EXIT_FAILURE);

	// Set a value
	int r = pakfire_parser_set(parser, "a", "a");
	assert_return(r == 0, EXIT_FAILURE);

	// Retrieve the value again
	value = pakfire_parser_get(parser, "a");
	assert_compare(value, "a", EXIT_FAILURE);

	// Append something to the value
	r = pakfire_parser_append(parser, "a", "b");
	assert_return(r == 0, EXIT_FAILURE);

	// Retrieve the value again
	value = pakfire_parser_get(parser, "a");
	assert_compare(value, "a b", EXIT_FAILURE);

	// Make a child parser
	PakfireParser subparser = pakfire_parser_create_child(parser, "child");
	assert_return(subparser, EXIT_FAILURE);

	// Try to get a again
	value = pakfire_parser_get(subparser, "a");
	assert_compare(value, "a b", EXIT_FAILURE);

	// Append something to the subparser
	r = pakfire_parser_append(subparser, "a", "c");
	assert_return(r == 0, EXIT_FAILURE);

	// The subparser should return "a b c"
	value = pakfire_parser_get(subparser, "a");
	assert_compare(value, "a b c", EXIT_FAILURE);

	// The original parser should remain unchanged
	value = pakfire_parser_get(parser, "a");
	assert_compare(value, "a b", EXIT_FAILURE);

	// Set another value
	r = pakfire_parser_append(subparser, "b", "1");
	assert_return(r == 0, EXIT_FAILURE);

	// Merge the two parsers
	pakfire_parser_merge(parser, subparser);

	// Now a should have changed to "a b c"
	value = pakfire_parser_get(parser, "a");
	assert_compare(value, "a b c", EXIT_FAILURE);

	// Set a variable
	r = pakfire_parser_set(parser, "c", "%{b}");
	assert_return(r == 0, EXIT_FAILURE);

	// Get the value of c
	value = pakfire_parser_get(parser, "c");
	assert_compare(value, "1", EXIT_FAILURE);

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
